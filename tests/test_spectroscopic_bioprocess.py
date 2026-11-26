import math
import random
import runpy
from pathlib import Path

import pytest
from spectroscopic_bioprocess.bioreactor import SpectroscopicBioreactor

from synthetic_lab import Lab

STUDY = runpy.run_path(str(Path(__file__).parents[1] / "examples/optimize_bioprocess.py"))


@pytest.mark.parametrize("kla", [0.0, 28.0, 300.0])
def test_oxygen_transfer_matches_closed_form_without_substrate(kla):
    model = SpectroscopicBioreactor({"initial_substrate": 0.0, "variation": 0.0})
    state = model.initial(random.Random(3))
    initial_oxygen = state["oxygen_percent"]
    state["kla_h"] = kla
    model.advance(state, 20.0)
    expected = 100.0 + (initial_oxygen - 100.0) * math.exp(-kla * 20.0 / 3600.0)
    assert state["oxygen_percent"] == pytest.approx(expected, abs=1e-10)


def test_closed_vessel_oxygen_budget_includes_feed_dilution_and_actual_growth():
    model = SpectroscopicBioreactor({"variation": 0, "maximum_volume": 1.1})
    state = model.initial(random.Random(3))
    state["kla_h"] = 0.0
    state["feed_rate_l_h"] = 0.1
    initial_oxygen = state["oxygen_percent"] * state["volume_l"]
    initial_biomass = state["biomass_g"]
    model.advance(state, 14400.0)
    consumed = model.config["oxygen_uptake"] * (state["biomass_g"] - initial_biomass)
    assert state["oxygen_percent"] * state["volume_l"] + consumed == pytest.approx(
        initial_oxygen, abs=1e-9
    )
    assert 0.0 <= state["oxygen_percent"] <= 100.0


def test_feed_stops_in_the_step_that_reaches_capacity():
    model = SpectroscopicBioreactor({"maximum_volume": 1.001, "variation": 0})
    state = model.initial(random.Random(3))
    state["feed_rate_l_h"] = 0.18
    model.advance(state, 20.0)
    assert state["volume_l"] == pytest.approx(1.001)
    assert state["feed_rate_l_h"] == 0.0


@pytest.mark.parametrize("kla", [0.0, 2.0, 30.0, 120.0])
def test_culture_trajectory_converges_with_smaller_time_steps(kla):
    model = SpectroscopicBioreactor({"variation": 0})
    coarse = model.initial(random.Random(3))
    coarse.update(kla_h=kla, feed_rate_l_h=0.05, induction=0.8)
    fine = dict(coarse)
    model.advance(coarse, 21600.0)
    for _ in range(21600):
        model.advance(fine, 1.0)
    for key in ("biomass_g", "substrate_g", "product_g", "oxygen_percent"):
        assert coarse[key] == pytest.approx(fine[key], rel=0.003, abs=1e-9)


def test_raman_contrast_removes_nominal_substrate_and_biomass():
    model = SpectroscopicBioreactor({"variation": 0})
    state = model.initial(random.Random(3))
    state["product_g"] = 1.0
    baseline = STUDY["product_contrast"](model._raman(state))
    state["substrate_g"] *= 3
    state["biomass_g"] *= 5
    assert STUDY["product_contrast"](model._raman(state)) == pytest.approx(baseline)
    state["product_g"] = 2.0
    assert STUDY["product_contrast"](model._raman(state)) == pytest.approx(2.0 * baseline)


def test_induction_schedules_use_equal_elapsed_time_and_independent_branches():
    with Lab(":memory:") as lab:
        root = lab.create("spectroscopic-bioreactor", seed=41)
        root.act("wait", seconds=7200.0)
        initial_status = root.status()
        for schedule in STUDY["SCHEDULES"].values():
            _, result = STUDY["run_schedule"](root, schedule)
            assert result["elapsed_s"] == pytest.approx(14406.7, abs=1e-8)
        assert root.status() == initial_status


def test_substrate_balance_and_working_volume():
    model = SpectroscopicBioreactor({"variation": 0, "maximum_volume": 1.2})
    state = model.initial(random.Random(3))
    initial_substrate = state["substrate_g"]
    state["feed_rate_l_h"] = 0.20
    model.advance(state, 7200.0)
    assert state["volume_l"] == pytest.approx(1.2)
    assert state["feed_rate_l_h"] == 0.0
    assert state["substrate_g"] + state["substrate_consumed_g"] == pytest.approx(
        initial_substrate + state["substrate_fed_g"], abs=1e-9
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
