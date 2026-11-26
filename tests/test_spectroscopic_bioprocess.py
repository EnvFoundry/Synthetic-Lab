import random

import pytest
from spectroscopic_bioprocess.bioreactor import SpectroscopicBioreactor

from synthetic_lab import Lab


def test_substrate_balance_and_working_volume():
    model = SpectroscopicBioreactor({"variation": 0, "maximum_volume": 1.2})
    state = model.initial(random.Random(3))
    initial_substrate = state["substrate_g"]
    state["feed_rate_l_h"] = 0.20
    model.advance(state, 7200.0)
    assert state["volume_l"] == pytest.approx(1.2)
    assert state["feed_rate_l_h"] == 0.0
    assert (
        state["substrate_g"] + state["substrate_consumed_g"]
        == pytest.approx(initial_substrate + state["substrate_fed_g"], abs=1e-9)
    )
    assert min(state[key] for key in ("biomass_g", "substrate_g", "product_g")) >= 0.0


def test_aeration_changes_dissolved_oxygen():
    model = SpectroscopicBioreactor({"variation": 0})
    low = model.initial(random.Random(5))
    high = model.initial(random.Random(5))
    for state in (low, high):
        state["feed_rate_l_h"] = 0.05
        state["induction"] = 0.5
    low["kla_h"] = 2.0
    high["kla_h"] = 60.0
    model.advance(low, 7200.0)
    model.advance(high, 7200.0)
    assert high["oxygen_percent"] > low["oxygen_percent"]


def test_induction_trades_biomass_for_product():
    model = SpectroscopicBioreactor({"variation": 0})
    dark = model.initial(random.Random(7))
    induced = model.initial(random.Random(7))
    for state in (dark, induced):
        state["feed_rate_l_h"] = 0.05
        model.advance(state, 7200.0)
    induced["induction"] = 1.0
    model.advance(dark, 14400.0)
    model.advance(induced, 14400.0)
    dark_biomass, _, dark_product = model.concentrations(dark)
    induced_biomass, _, induced_product = model.concentrations(induced)
    assert induced_product > dark_product
    assert induced_biomass < dark_biomass


def test_optical_measurements_share_one_culture_state():
    model = SpectroscopicBioreactor({"variation": 0})
    state = model.initial(random.Random(11))
    state["feed_rate_l_h"] = 0.04
    state["induction"] = 0.8
    model.advance(state, 3600.0)
    rng = random.Random(17)
    od = model.perform(state, rng, "read", {"instrument": "od600"})
    fluorescence = model.perform(state, rng, "read", {"instrument": "fluorescence"})
    oxygen = model.perform(state, rng, "read", {"instrument": "optode"})
    raman = model.perform(state, rng, "read", {"instrument": "raman"})
    assert od["od600"]["value"] > 0.0
    assert fluorescence["reporter_fluorescence"]["value"] > 0.0
    assert 0.0 <= oxygen["dissolved_oxygen"]["value"] <= 100.0
    assert raman["raman_intensity"]["shape"] == [5]
    assert state["time_s"] == pytest.approx(3606.7)


def test_package_is_discovered_without_exposing_culture_state():
    catalogue = {description["name"]: description for description in Lab.catalogue()}
    description = catalogue["spectroscopic-bioreactor"]
    contract = description["research_contract"]
    assert set(contract["action_semantics"]) == set(description["actions"])
    assert {"od600", "reporter_fluorescence", "raman_intensity", "dissolved_oxygen"} <= set(
        contract["observables"]
    )

    with Lab(":memory:") as lab:
        experiment = lab.create("spectroscopic-bioreactor", seed=23)
        assert set(experiment.status()["configuration"]) == {
            "feed_rate_l_h",
            "kla_h",
            "temperature_setpoint_k",
            "induction_level",
        }
