import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from synthetic_lab import Lab

pybamm = pytest.importorskip("pybamm")
pytest.importorskip("pybamm_battery")

MODELS = ("pybamm-battery-spm", "pybamm-battery-spme", "pybamm-battery-dfn")


@pytest.mark.parametrize(
    "model",
    MODELS,
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
        session_id = cell.id

    source = Path(__file__).parents[1] / "src"
    client = """
import importlib.util,json,sys
sys.path.insert(0,sys.argv[1])
assert importlib.util.find_spec('pybamm') is None
assert importlib.util.find_spec('pybamm_battery') is None
from synthetic_lab import Lab
with Lab(sys.argv[2]) as lab:
    cell=lab.session(sys.argv[3])
    print(json.dumps(cell.submit('step',current=2,seconds=60,operation_id='pulse')))
"""
    submitted = subprocess.run(
        [sys.executable, "-S", "-c", client, str(source), str(database), session_id],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(submitted.stdout)["status"] == "pending"
    worker = subprocess.run(
        [
            sys.executable,
            "-m",
            "synthetic_lab.cli",
            "--db",
            str(database),
            "worker",
            "--model",
            "pybamm-battery-spm",
            "--once",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(worker.stdout)["status"] == "succeeded"
    with Lab(database) as lab:
        result = lab.operation(session_id, "pulse")["result"]
        assert result["end_s"] == 60.0
        assert result["observations"]["terminal_voltage"]["value"] > 0.0


def test_model_ladder_changes_the_high_current_prediction():
    voltages = {}
    with Lab(":memory:") as lab:
        for model in MODELS:
            cell = lab.create(
                model,
                config={"initial_soc": 0.8, "sample_period": 10.0},
            )
            result = cell.act("step", current=5.0, seconds=300.0)
            voltages[model] = result["observations"]["terminal_voltage"]["value"]
    assert max(voltages.values()) - min(voltages.values()) > 1e-5


@pytest.mark.parametrize("model", MODELS)
def test_reading_the_initial_state_does_not_add_a_rest_segment(model):
    with Lab(":memory:", artifact_threshold=10**7) as lab:
        observed = lab.create(model)
        untouched = observed.fork()
        for _ in range(2):
            result = observed.act("read", instrument="summary")
            assert result["start_s"] == result["end_s"] == 0
            assert result["configuration"]["protocol_segments"] == 0
            assert result["observations"]["current"]["value"] == 0
            assert result["observations"]["state_of_charge"]["value"] == 0.8
        trace = observed.act("trace")["observations"]["battery_trace"]
        assert trace["shape"] == [1]
        assert trace["value"]["time_s"] == [0.0]
        assert trace["value"]["discharge_capacity_ah"] == [0.0]
        actual = observed.act("step", current=2, seconds=60)
        reference = untouched.act("step", current=2, seconds=60)
        assert actual["observations"] == reference["observations"]
        assert actual["end_s"] == reference["end_s"] == 60


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("initial_soc,current,cutoff", [(0.2, 5.0, 2.5), (0.5, -5.0, 4.2)])
def test_voltage_cutoff_then_resume_rest_and_reverse_current(
    tmp_path, model, initial_soc, current, cutoff
):
    database = tmp_path / "cutoff.sqlite"
    with Lab(database) as lab:
        cell = lab.create(model, config={"initial_soc": initial_soc})
        stopped = cell.act("step", current=current, seconds=3600)
        elapsed = stopped["end_s"]
        assert 0 < elapsed < 3600
        observations = stopped["observations"]
        assert observations["terminal_voltage"]["value"] == pytest.approx(cutoff, abs=1e-6)
        assert "[experiment]" in observations["solver_termination"]["value"]
        capacity = observations["discharge_capacity"]["value"]
        assert capacity == pytest.approx(current * elapsed / 3600, abs=1e-8)
        assert observations["state_of_charge"]["value"] == pytest.approx(
            initial_soc - capacity / 5.0
        )
        clone = cell.fork()
        ids = [cell.id, clone.id]

    with Lab(database) as lab:
        results = []
        for session_id in ids:
            cell = lab.session(session_id)
            rest = cell.act("step", current=0, seconds=100)
            assert rest["end_s"] - rest["start_s"] == pytest.approx(100)
            assert rest["observations"]["current"]["value"] == 0
            assert rest["observations"]["discharge_capacity"]["value"] == pytest.approx(capacity)
            reverse = -math.copysign(1.0, current)
            result = cell.act("step", current=reverse, seconds=100)
            assert result["end_s"] == pytest.approx(elapsed + 200)
            assert result["observations"]["current"]["value"] == reverse
            assert result["observations"]["discharge_capacity"]["value"] == pytest.approx(
                capacity + reverse * 100 / 3600, abs=1e-8
            )
            results.append(result["observations"])
        assert results[0] == results[1]


def test_appending_the_same_current_preserves_the_committed_trace():
    with Lab(":memory:", artifact_threshold=10**7) as lab:
        cell = lab.create("pybamm-battery-spm", config={"sample_period": 5})
        cell.act("step", current=2, seconds=7)
        first = cell.act("trace")["observations"]["battery_trace"]["value"]
        result = cell.act("step", current=2, seconds=11)
        assert result["configuration"]["protocol_segments"] == 2
        full = cell.act("trace")["observations"]["battery_trace"]["value"]
        count = len(first["time_s"])
        for field in first:
            assert full[field][:count] == pytest.approx(first[field], abs=1e-10)
        assert full["time_s"][-1] == 18


def test_unavailable_current_step_leaves_the_previous_state_usable():
    with Lab(":memory:") as lab:
        cell = lab.create("pybamm-battery-spm", config={"initial_soc": 0.2})
        stopped = cell.act("step", current=5, seconds=3600)
        with pytest.raises(pybamm.SolverError, match="infeasible"):
            cell.act("step", current=10, seconds=60)
        unchanged = cell.act("read", instrument="summary")
        assert unchanged["observations"] == stopped["observations"]
        assert unchanged["end_s"] == stopped["end_s"]
        rest = cell.act("step", current=0, seconds=60)
        assert rest["end_s"] - stopped["end_s"] == pytest.approx(60)


def test_nominal_capacity_soc_is_not_clipped_to_hide_a_capacity_difference():
    with Lab(":memory:") as lab:
        cell = lab.create("pybamm-battery-spm", config={"initial_soc": 0.05})
        result = cell.act("step", current=0.1, seconds=14400)
        outputs = result["observations"]
        assert outputs["terminal_voltage"]["value"] == pytest.approx(2.5)
        expected = 0.05 - outputs["discharge_capacity"]["value"] / 5.0
        assert expected < 0
        assert outputs["state_of_charge"]["value"] == expected


def test_solver_error_after_a_completed_segment_does_not_commit_its_partial_solution(monkeypatch):
    with Lab(":memory:") as lab:
        cell = lab.create("pybamm-battery-spm")
        before = cell.act("step", current=2, seconds=30)
        original_step = pybamm.IDAKLUSolver.step

        def interrupted_step(solver, old_solution, *args, **kwargs):
            if old_solution is not None and old_solution.t[-1] >= 30:
                raise pybamm.SolverError("interrupted numerical solve")
            return original_step(solver, old_solution, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(pybamm.IDAKLUSolver, "step", interrupted_step)
            with pytest.raises(pybamm.SolverError, match="interrupted numerical solve"):
                cell.act("step", current=0, seconds=30)
        after = cell.act("read", instrument="summary")
        assert after["observations"] == before["observations"]
        assert after["end_s"] == before["end_s"]
        continued = cell.act("step", current=0, seconds=30)
        assert continued["end_s"] == 60
