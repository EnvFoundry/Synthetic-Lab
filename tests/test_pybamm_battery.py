import math

import pytest

from synthetic_lab import Lab, Worker

pytest.importorskip("pybamm")
pytest.importorskip("pybamm_battery")


@pytest.mark.parametrize(
    "model",
    ("pybamm-battery-spm", "pybamm-battery-spme", "pybamm-battery-dfn"),
)
def test_solver_backed_models_are_discovered_and_produce_physical_endpoints(model):
    with Lab(":memory:") as lab:
        assert model in {description["name"] for description in lab.catalogue()}
        cell = lab.create(
            model,
            seed=3,
            config={"initial_soc": 0.75, "sample_period": 10.0},
        )
        result = cell.act("step", current=2.0, seconds=60.0)
        observations = result["observations"]
        voltage = observations["terminal_voltage"]["value"]
        temperature = observations["cell_temperature"]["value"]
        soc = observations["state_of_charge"]["value"]
        assert 2.5 < voltage < 4.5
        assert 273.15 < temperature < 340.0
        assert 0.0 < soc < 0.75
        assert all(math.isfinite(value) for value in (voltage, temperature, soc))


def test_same_protocol_is_repeatable_after_persistence_and_fork(tmp_path):
    database = tmp_path / "battery.sqlite"
    with Lab(database) as lab:
        cell = lab.create(
            "pybamm-battery-spm",
            seed=9,
            config={"initial_soc": 0.8, "sample_period": 5.0},
        )
        first = cell.act("step", current=3.0, seconds=90.0)
        clone = cell.fork()
        clone_id = clone.id
        cell_id = cell.id
        assert first["observations"]["terminal_voltage"]["value"] > 0.0

    with Lab(database) as lab:
        original = lab.session(cell_id)
        clone = lab.session(clone_id)
        original_result = original.act("step", current=0.0, seconds=120.0)
        clone_result = clone.act("step", current=0.0, seconds=120.0)
        assert original_result["observations"] == clone_result["observations"]


def test_trace_is_external_and_reused_without_copying_the_solver_series():
    with Lab(":memory:", artifact_threshold=256) as lab:
        cell = lab.create(
            "pybamm-battery-spme",
            config={"initial_soc": 0.7, "sample_period": 2.0},
        )
        cell.act("step", current=4.0, seconds=60.0)
        first = cell.act("trace")["observations"]["battery_trace"]
        second = cell.act("trace")["observations"]["battery_trace"]
        reference = first["value"]
        assert first["shape"][0] >= 2
        assert first["fields"]["terminal_voltage_v"] == "V"
        assert "$artifact" in reference
        assert reference == second["value"]
        trajectory = lab.read_artifact(reference["$artifact"]["id"])
        assert len(trajectory["time_s"]) == first["shape"][0]
        assert trajectory["terminal_voltage_v"][-1] > 0.0


def test_pybamm_operation_runs_through_a_domain_worker(tmp_path):
    database = tmp_path / "worker.sqlite"
    with Lab(database) as lab:
        cell = lab.create(
            "pybamm-battery-spm",
            config={"initial_soc": 0.8, "sample_period": 10.0},
        )
        submitted = cell.submit("step", current=2.0, seconds=60.0, operation_id="pulse")
        assert submitted["status"] == "pending"
        session_id = cell.id

    with Lab(database) as lab:
        completed = Worker(
            lab,
            models=("pybamm-battery-spm",),
            worker_id="battery-worker",
        ).run_once()
        assert completed["status"] == "succeeded"
        result = lab.operation(session_id, "pulse")["result"]
        assert result["end_s"] == 60.0
        assert result["observations"]["terminal_voltage"]["value"] > 0.0


def test_model_ladder_changes_the_high_current_prediction():
    voltages = {}
    with Lab(":memory:") as lab:
        for model in ("pybamm-battery-spm", "pybamm-battery-spme", "pybamm-battery-dfn"):
            cell = lab.create(
                model,
                config={"initial_soc": 0.8, "sample_period": 10.0},
            )
            result = cell.act("step", current=5.0, seconds=300.0)
            voltages[model] = result["observations"]["terminal_voltage"]["value"]
    assert max(voltages.values()) - min(voltages.values()) > 1e-5
