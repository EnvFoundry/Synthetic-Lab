"""Mass, oxygen and finite-response dynamics; times are seconds at the boundary."""

import math


def concentrations(state):
    volume = state["volume_l"]
    return (
        state["biomass_g"] / volume,
        state["substrate_g"] / volume,
        state["product_g"] / volume,
    )


def _rates(config, state):
    biomass, substrate, _ = concentrations(state)
    oxygen = state["oxygen_percent"]
    temperature_factor = math.exp(
        -(
            ((state["temperature_k"] - config["temperature_optimum"]) / config["temperature_width"])
            ** 2
        )
    )
    substrate_factor = substrate / (config["ks"] + substrate) if substrate > 0.0 else 0.0
    oxygen_factor = oxygen / (config["ko"] + oxygen) if oxygen > 0.0 else 0.0
    burden_factor = math.exp(-1.5 * state["burden"])
    mu = (
        config["mu_max"]
        * state["growth_scale"]
        * substrate_factor
        * oxygen_factor
        * temperature_factor
        * burden_factor
    )
    product_factor = oxygen / (15.0 + oxygen) if oxygen > 0.0 else 0.0
    qp = (
        config["qp_max"]
        * state["product_scale"]
        * state["reporter"]
        * product_factor
        * math.exp(-0.6 * state["burden"])
    )
    return mu, qp, biomass


def _step(config, state, seconds):
    dt_h = seconds / 3600.0
    if dt_h <= 0.0:
        return

    thermal_decay = math.exp(-seconds / config["thermal_tau"])
    state["temperature_k"] = (
        state["temperature_setpoint_k"]
        + (state["temperature_k"] - state["temperature_setpoint_k"]) * thermal_decay
    )

    reporter_decay = math.exp(-dt_h / config["reporter_tau"])
    state["reporter"] = (
        state["induction"] + (state["reporter"] - state["induction"]) * reporter_decay
    )

    target_burden = min(
        1.0,
        0.75 * state["induction"] + 0.35 * max(0.0, 30.0 - state["oxygen_percent"]) / 30.0,
    )
    burden_decay = math.exp(-dt_h / config["burden_tau"])
    state["burden"] = target_burden + (state["burden"] - target_burden) * burden_decay

    room = max(0.0, config["maximum_volume"] - state["volume_l"])
    feed_volume = min(room, state["feed_rate_l_h"] * dt_h)
    feed_substrate = feed_volume * config["feed_substrate"]
    previous_volume = state["volume_l"]
    state["volume_l"] += feed_volume
    # The feed contains no dissolved oxygen in this reference model.
    state["oxygen_percent"] *= previous_volume / state["volume_l"]
    state["substrate_g"] += feed_substrate
    state["substrate_fed_g"] += feed_substrate
    if config["maximum_volume"] - state["volume_l"] <= 1e-12:
        state["feed_rate_l_h"] = 0.0

    mu, qp, _ = _rates(config, state)
    potential_growth = state["biomass_g"] * math.expm1(mu * dt_h)
    growth_substrate = potential_growth / config["yield_xs"]
    potential_product = qp * state["biomass_g"] * dt_h
    product_substrate = potential_product / config["yield_ps"]
    required = growth_substrate + product_substrate
    if required > state["substrate_g"] and required > 0.0:
        scale = state["substrate_g"] / required
        potential_growth *= scale
        potential_product *= scale
        growth_substrate *= scale
        product_substrate *= scale

    # Integrate transfer exactly for this step's constant growth-associated demand.
    # Uptake is based on realized growth, including substrate and oxygen limits.
    kla = state["kla_h"]
    exchanged = -math.expm1(-kla * dt_h)
    response_h = exchanged / kla if kla > 0.0 else dt_h
    oxygen_without_uptake = state["oxygen_percent"] * (1.0 - exchanged) + 100.0 * exchanged
    demand = config["oxygen_uptake"] * potential_growth / (state["volume_l"] * dt_h)
    oxygen_used = demand * response_h
    if oxygen_used > oxygen_without_uptake:
        scale = oxygen_without_uptake / oxygen_used
        potential_growth *= scale
        potential_product *= scale
        growth_substrate *= scale
        product_substrate *= scale
        oxygen_used = oxygen_without_uptake
    state["oxygen_percent"] = oxygen_without_uptake - oxygen_used

    consumed = growth_substrate + product_substrate
    state["biomass_g"] += potential_growth
    state["product_g"] += potential_product
    state["substrate_g"] = max(0.0, state["substrate_g"] - consumed)
    state["substrate_consumed_g"] += consumed

    state["time_s"] += seconds


def advance(config, state, seconds):
    remaining = seconds
    while remaining > 1e-12:
        biomass, substrate, _ = concentrations(state)
        turnover = (
            config["oxygen_uptake"]
            * config["mu_max"]
            * state["growth_scale"]
            * biomass
            * substrate
            / (config["ks"] + substrate)
            / (config["ko"] + state["oxygen_percent"])
        )
        step = min(20.0, 900.0 / max(state["kla_h"], turnover, 1.0), remaining)
        _step(config, state, step)
        remaining -= step
