import math
import random

import pytest

from synthetic_lab import Lab
from synthetic_lab.calibration import fit_thermal
from synthetic_lab.models.battery import Battery
from synthetic_lab.models.optics import FiberBench
from synthetic_lab.models.thermal import ThermalBench
from synthetic_lab.quantities import quantity


def test_units_and_absolute_temperature():
    assert quantity({"value": 30, "unit": "mW"}, "W") == 0.03
    assert quantity({"value": 20, "unit": "degC"}, "K") == 293.15
    assert quantity({"value": 180, "unit": "deg"}, "rad") == math.pi
    with pytest.raises(ValueError):
        quantity({"value": 1, "unit": "A"}, "K")


def test_thermal_energy_balance_steady_limit_and_partition():
    model = ThermalBench({"variation": 0})
    initial = model.initial(random.Random(7))
    initial["voltage"] = 4
    divided = dict(initial)
    model.advance(initial, 1000)
    for _ in range(100):
        model.advance(divided, 10)
    assert divided["temperature"] == pytest.approx(initial["temperature"], abs=1e-10)
    assert initial["energy_j"] == pytest.approx(800)
    stored = 12 * (initial["temperature"] - 295.15)
    assert stored + initial["lost_heat_j"] == pytest.approx(initial["energy_j"])
    model.advance(initial, 3000)
    assert initial["temperature"] == pytest.approx(303.15, abs=1e-7)


def test_added_electrical_measurement_identifies_heat_resistance():
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=11, config={"thermal_resistance": 12, "variation": 0})
        assert set(session.act("read")["observations"]) == {"temperature"}
        session.act("connect", channel="electrical")
        session.act("connect", channel="ambient")
        records = []
        for voltage in (0, 2, 4):
            session.act("supply", voltage=voltage)
            session.act("wait", seconds=2400)
            records.append(session.act("read"))
        fit = fit_thermal(records)
        assert fit["thermal_resistance_k_per_w"] == pytest.approx(12, abs=0.2)
        assert fit["source"] == "simulation"


def test_gaussian_coupling_and_meter_saturation():
    model = FiberBench({"drift": 0})
    state = model.initial(random.Random(1))
    state.update(power=0.01, set_power=0.01, x=state["center_x"], y=state["center_y"])
    source, maximum = model.signal(state)
    assert maximum / source == pytest.approx(0.85)
    state["x"] += model.config["width"]
    assert model.signal(state)[1] / maximum == pytest.approx(math.exp(-0.5))
    state.update(x=state["center_x"], power=0.05, set_power=0.05)
    result = model.perform(state, random.Random(1), "read", {"detector": "power"})
    assert result["coupled_power"]["saturated"]
    assert result["coupled_power"]["value"] == 0.02


def test_camera_exposure_and_shutter():
    model = FiberBench({"drift": 0})
    state = model.initial(random.Random(7))
    state.update(power=0.05, set_power=0.05, x=state["center_x"], y=state["center_y"], exposure=0.1)
    image = model.perform(state, random.Random(2), "read", {"detector": "camera"})["image"]
    assert image["saturated_pixels"] > 0
    state["shutter"] = "closed"
    dark = model.perform(state, random.Random(2), "read", {"detector": "camera"})["image"]
    assert dark["saturated_pixels"] == 0
    assert max(map(max, dark["value"])) < 50


def test_battery_charge_balance_relaxation_and_cutoff():
    model = Battery({"variation": 0})
    state = model.initial(random.Random(4))
    charge = state["charge_c"]
    state["current"] = 1
    model.advance(state, 90)
    assert state["charge_c"] == pytest.approx(charge - 90)
    assert state["polarization_v"] == pytest.approx(0.03 * (1 - math.exp(-2)))
    assert state["temperature"] > 295.15
    state["current"] = 0
    polarization = state["polarization_v"]
    model.advance(state, 180)
    assert state["polarization_v"] == pytest.approx(polarization * math.exp(-4))
    state.update(charge_c=0.5, current=2)
    model.advance(state, 10)
    assert state["charge_c"] == 0
    assert state["current"] == 0
    assert state["protection"] == "tripped"


def test_calibration_rejects_unidentified_or_mixed_measurements():
    with pytest.raises(ValueError, match="three"):
        fit_thermal([])
    record = {
        "source": "measurement",
        "observations": {
            "temperature": {"value": 300, "unit": "K"},
            "ambient": {"value": 295, "unit": "K"},
            "voltage": {"value": 4, "unit": "V"},
            "current": {"value": 0.2, "unit": "A"},
        },
    }
    with pytest.raises(ValueError, match="distinct"):
        fit_thermal([record] * 3)
    with pytest.raises(ValueError, match="separately"):
        fit_thermal([record, dict(record, source="simulation")])
