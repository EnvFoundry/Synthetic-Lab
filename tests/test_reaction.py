import random

import pytest

from synthetic_lab import Lab
from synthetic_lab.models.reaction import ReactionBench
from synthetic_lab.quantities import quantity


def state(model):
    return model.initial(random.Random(7))


def test_reaction_units_and_catalogue_contract():
    assert quantity({"value": 250, "unit": "mL"}, "L") == 0.25
    assert quantity({"value": 50, "unit": "kJ/mol"}, "J/mol") == 50000
    catalogue = {description["name"]: description for description in Lab.catalogue()}
    assert {"battery", "fiber", "reaction", "thermal"} <= set(catalogue)
    for name in ("battery", "fiber", "reaction", "thermal"):
        contract = catalogue[name]["research_contract"]
        assert contract["schema_version"] == 1
        assert set(contract["action_semantics"]) == set(catalogue[name]["actions"])
        assert contract["questions"]
        assert contract["validity"]["conditions"]
        assert contract["validity"]["limitations"]


def test_mass_balance_and_nonnegative_state():
    model = ReactionBench({"variation": 0})
    experiment = state(model)
    total = experiment["a"] + experiment["b"] + experiment["c"]
    experiment["setpoint"] = 365
    model.advance(experiment, 1800)
    assert experiment["a"] + experiment["b"] + experiment["c"] == pytest.approx(total, abs=1e-12)
    assert min(experiment[species] for species in ("a", "b", "c")) >= 0
    assert 0 <= experiment["activity"] <= 1


def test_temperature_schedule_changes_conversion_and_selectivity():
    model = ReactionBench({"variation": 0})
    low = state(model)
    high = state(model)
    low["setpoint"] = 325
    high["setpoint"] = 385
    model.advance(low, 600)
    model.advance(high, 600)
    assert high["a"] < low["a"]
    assert high["c"] > low["c"]

    selected = state(model)
    selected["setpoint"] = 355
    model.advance(selected, 300)
    first_b = selected["b"]
    model.advance(selected, 2400)
    assert first_b > 0
    assert selected["b"] < first_b
    assert selected["c"] > 0


def test_measurements_share_one_evolving_latent_state():
    model = ReactionBench({"variation": 0})
    experiment = state(model)
    experiment["setpoint"] = 360
    model.advance(experiment, 500)
    spectrum = model.perform(experiment, random.Random(2), "read", {"instrument": "spectrometer"})
    composition = model.perform(
        experiment, random.Random(2), "read", {"instrument": "chromatograph"}
    )
    assert spectrum["absorbance"]["shape"] == [3]
    assert set(composition) == {"a", "b", "c"}
    assert experiment["time_s"] == pytest.approx(521)
    assert experiment["reads"] == 2


def test_runtime_hides_species_state_and_preserves_branches():
    with Lab(":memory:") as lab:
        root = lab.create("reaction", seed=9, config={"variation": 0})
        hot = root.fork()
        cool = root.fork()
        hot.act("set_temperature", setpoint=400)
        cool.act("set_temperature", setpoint=325)
        hot.act("wait", seconds=600)
        cool.act("wait", seconds=600)
        hot_b = hot.act("read", instrument="chromatograph")["observations"]["b"]["value"]
        cool_b = cool.act("read", instrument="chromatograph")["observations"]["b"]["value"]
        assert hot_b != pytest.approx(cool_b)
        assert set(root.status()["configuration"]) == {
            "measurement_count",
            "temperature_setpoint_k",
            "thermal_protection",
        }
