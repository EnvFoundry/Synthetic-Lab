import concurrent.futures
import json

import pytest

from synthetic_lab import Lab
from synthetic_lab.models.thermal import ThermalBench
from synthetic_lab.runtime import Conflict


@pytest.mark.parametrize(
    "model,action,params",
    [
        ("thermal", "read", {}),
        ("fiber", "read", {"detector": "camera"}),
        ("battery", "read", {}),
    ],
)
def test_resume_preserves_full_state_and_random_sequence(tmp_path, model, action, params):
    path = tmp_path / "lab.sqlite"
    with Lab(path) as lab:
        session = lab.create(model, seed=9)
        session.act(action, **params)
        branch = session.fork()
        expected = branch.act(action, **params)
        session_id = session.id
    with Lab(path) as reopened:
        actual = reopened.session(session_id).act(action, **params)
        assert actual["observations"] == expected["observations"]
        assert actual["configuration"] == expected["configuration"]
        assert actual["end_s"] == expected["end_s"]


def test_history_fork_and_original_are_independent():
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=1)
        session.act("supply", voltage=4)
        session.act("wait", seconds=100)
        old = session.fork(at_revision=1)
        assert old.status()["time_s"] == 0.02
        assert old.status()["parent_revision"] == 1
        assert old.status()["lineage"] == session.id
        old.act("supply", voltage=0)
        assert session.status()["configuration"]["supply_v"] == 4
        assert old.history()[0]["revision"] == 1


def test_duplicate_request_and_version_conflict():
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=1)
        first = session.act("wait", seconds=10, operation_id="request-1", expected_revision=0)
        assert (
            session.act("wait", seconds=10, operation_id="request-1", expected_revision=0) == first
        )
        assert session.status()["revision"] == 1
        with pytest.raises(Conflict):
            session.act("wait", seconds=11, operation_id="request-1")
        with pytest.raises(Conflict):
            session.act("wait", seconds=10, expected_revision=0)
        assert len(session.history()) == 1


def test_concurrent_workers_deduplicate(tmp_path):
    database = tmp_path / "lab.sqlite"
    with Lab(database) as lab:
        identifier = lab.create("thermal", seed=4).id

    def operate(_):
        with Lab(database) as worker:
            return worker.session(identifier).act("wait", seconds=7, operation_id="shared")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(operate, range(16)))
    assert all(result == results[0] for result in results)
    with Lab(database) as lab:
        assert lab.status(identifier)["time_s"] == 7
        assert len(lab.history(identifier)) == 1


def test_failed_operation_rolls_back_state_rng_history(monkeypatch):
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=1)
        original = session.status()
        reference = session.fork()
        perform = ThermalBench.perform

        def failing(model, state, rng, action, params):
            state["time_s"] += 100
            rng.random()
            raise RuntimeError("Interrupted during calculation")

        monkeypatch.setattr(ThermalBench, "perform", failing)
        with pytest.raises(RuntimeError):
            session.act("read", operation_id="retry")
        assert session.status() == original
        assert session.history() == []
        monkeypatch.setattr(ThermalBench, "perform", perform)
        assert (
            session.act("read", operation_id="retry")["observations"]
            == reference.act("read")["observations"]
        )


@pytest.mark.parametrize(
    "params",
    [
        {"voltage": float("nan")},
        {"voltage": True},
        {"voltage": 6},
        {"voltage": -1},
        {"v": 2},
        {"voltage": {"value": 1, "unit": "W"}},
    ],
)
def test_invalid_actions_leave_state_unchanged(params):
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=1)
        original = session.status()
        with pytest.raises(ValueError):
            session.act("supply", **params)
        assert session.status() == original


def test_export_excludes_latent_parameters_and_random_state(tmp_path):
    with Lab(":memory:") as lab:
        session = lab.create("thermal", seed=1)
        session.act("read")
        path = tmp_path / "observations.jsonl"
        assert session.export(path) == 1
        result = json.loads(path.read_text())
        assert "temperature" in result["observations"]
        assert all(
            key not in path.read_text()
            for key in ("thermal_resistance", "heater_resistance", "supply_gain", '"rng"', '"seed"')
        )


def test_model_version_changes_require_explicit_migration(monkeypatch):
    with Lab(":memory:") as lab:
        session = lab.create("thermal")
        monkeypatch.setattr(ThermalBench, "version", "future")
        with pytest.raises(Conflict, match="version"):
            session.act("read")
