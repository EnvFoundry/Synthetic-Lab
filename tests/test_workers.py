import concurrent.futures
import sqlite3
import threading
import time

from synthetic_lab import Lab, Worker
from synthetic_lab.models.thermal import ThermalBench


def test_slow_solver_does_not_hold_database_write_lock(tmp_path, monkeypatch):
    database = tmp_path / "lab.sqlite"
    with Lab(database) as lab:
        slow = lab.create("thermal", seed=1)
        fast = lab.create("thermal", seed=2)

    started = threading.Event()
    release = threading.Event()
    original = ThermalBench.perform

    def delayed(model, state, rng, action, params):
        if action == "wait" and params["seconds"] == 13:
            started.set()
            release.wait(1.5)
        return original(model, state, rng, action, params)

    monkeypatch.setattr(ThermalBench, "perform", delayed)

    def run_slow():
        with Lab(database) as lab:
            return lab.session(slow.id).act("wait", seconds=13, operation_id="slow")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future = executor.submit(run_slow)
        assert started.wait(1.0)
        before = time.perf_counter()
        with Lab(database) as lab:
            lab.session(fast.id).act("wait", seconds=1, operation_id="fast")
        elapsed = time.perf_counter() - before
        release.set()
        future.result(timeout=2.0)

    assert elapsed < 0.5


def test_submitted_operation_continues_in_a_new_process_context(tmp_path):
    database = tmp_path / "lab.sqlite"
    with Lab(database) as lab:
        session = lab.create("thermal", seed=4)
        submitted = session.submit("wait", seconds=7, operation_id="queued")
        assert submitted["status"] == "pending"
        session_id = session.id

    with Lab(database) as lab:
        result = Worker(lab, models=("thermal",), worker_id="thermal-worker").run_once()
        assert result["status"] == "succeeded"

    with Lab(database) as lab:
        completed = lab.operation(session_id, "queued")
        assert completed["result"]["end_s"] == 7
        assert lab.status(session_id)["revision"] == 1


def test_operations_on_one_session_follow_submission_order(tmp_path):
    with Lab(tmp_path / "lab.sqlite") as lab:
        session = lab.create("thermal", seed=8)
        session.submit("wait", seconds=2, operation_id="first")
        session.submit("wait", seconds=3, operation_id="second")
        worker = Worker(lab, models=("thermal",), worker_id="thermal-worker")
        worker.run_once()
        worker.run_once()
        history = session.history()
        assert [record["operation_id"] for record in history] == ["first", "second"]
        assert [record["end_s"] for record in history] == [2, 5]


def test_worker_claims_only_installed_domain_models(tmp_path):
    with Lab(tmp_path / "lab.sqlite") as lab:
        thermal = lab.create("thermal", seed=3)
        battery = lab.create("battery", seed=4)
        thermal.submit("wait", seconds=1, operation_id="thermal")
        battery.submit("wait", seconds=1, operation_id="battery")
        Worker(lab, models=("thermal",), worker_id="thermal-worker").run_once()
        assert thermal.operation("thermal")["status"] == "succeeded"
        assert battery.operation("battery")["status"] == "pending"


def test_schema_one_database_is_migrated_to_queued_operations(tmp_path):
    database = tmp_path / "old.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, model TEXT NOT NULL, model_version TEXT NOT NULL,
                config TEXT NOT NULL, seed INTEGER NOT NULL, lineage TEXT NOT NULL,
                parent TEXT, parent_revision INTEGER, revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL
            );
            CREATE TABLE snapshots (
                session TEXT NOT NULL REFERENCES sessions(id), revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL, PRIMARY KEY(session, revision)
            );
            CREATE TABLE operations (
                session TEXT NOT NULL REFERENCES sessions(id), id TEXT NOT NULL,
                revision INTEGER NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(session, id), UNIQUE(session, revision)
            );
            CREATE TABLE profiles (
                session TEXT PRIMARY KEY REFERENCES sessions(id), provenance TEXT NOT NULL
            );
            PRAGMA user_version = 1;
            """
        )
    with Lab(database):
        pass
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(operations)")}
        assert {"status", "base_revision", "worker", "claim_until"} <= columns
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "artifacts" in tables
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4


def test_history_iterator_reads_in_batches(tmp_path):
    with Lab(tmp_path / "lab.sqlite") as lab:
        session = lab.create("thermal", seed=6)
        for index in range(7):
            session.act("wait", seconds=1, operation_id=f"step-{index}")
        records = list(lab.iter_history(session.id, batch_size=2))
        assert [record["revision"] for record in records] == list(range(1, 8))


def test_reclaimed_operation_does_not_accept_the_previous_attempt(tmp_path):
    import pytest

    from synthetic_lab.runtime import Conflict

    with Lab(tmp_path / "claim.sqlite") as lab:
        session = lab.create("thermal", seed=3)
        session.submit("wait", seconds=7, operation_id="work")
        first = lab._claim("same-worker", models=("thermal",))
        lab._db.execute("UPDATE operations SET claim_until = 0")
        second = lab._claim("same-worker", models=("thermal",))
        assert first["attempt"] != second["attempt"]
        assert not lab._extend_claim(first)
        with pytest.raises(Conflict, match="owned"):
            lab._execute(first)
        assert session.operation("work")["status"] == "running"
        lab._execute(second)
        assert session.status()["time_s"] == 7
        assert len(session.history()) == 1


def test_client_without_domain_installation_submits_to_separate_worker(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    database = tmp_path / "separate.sqlite"
    with Lab(database) as lab:
        session_id = lab.create("thin-film", seed=3).id
    source = Path(__file__).parents[1] / "src"
    client = """
import json,sys
sys.path.insert(0,sys.argv[1])
from synthetic_lab import Lab
with Lab(sys.argv[2]) as lab:
    s=lab.session(sys.argv[3])
    assert lab.describe_session(s.id)['name']=='thin-film'
    branch=s.fork(at_revision=0)
    assert branch.status()['time_s']==0
    print(json.dumps(s.submit('wait',seconds={'value':1,'unit':'s'},operation_id='remote')))
assert not any(name.startswith('optical_metrology') for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", client, str(source), str(database), session_id],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["status"] == "pending"
    worker = subprocess.run(
        [
            sys.executable,
            "-m",
            "synthetic_lab.cli",
            "--db",
            str(database),
            "worker",
            "--model",
            "thin-film",
            "--once",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(worker.stdout)["status"] == "succeeded"
    with Lab(database) as lab:
        assert lab.operation(session_id, "remote")["result"]["end_s"] == 1


def test_short_claim_is_renewed_during_solver_execution(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    original = ThermalBench.perform

    def delayed(model, state, rng, action, params):
        started.set()
        assert release.wait(3)
        return original(model, state, rng, action, params)

    monkeypatch.setattr(ThermalBench, "perform", delayed)
    database = tmp_path / "renew.sqlite"
    with Lab(database) as worker, Lab(database) as observer:
        session = worker.create("thermal", seed=4)
        session.submit("wait", seconds=1)
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            future = executor.submit(Worker(worker, lease_seconds=0.12).run_once)
            assert started.wait(2)
            try:
                time.sleep(0.3)
                assert observer._claim("other", models=("thermal",)) is None
            finally:
                release.set()
            assert future.result(timeout=3)["status"] == "succeeded"


def test_branch_uses_committed_state_while_parent_operation_is_running(tmp_path):
    with Lab(tmp_path / "branch.sqlite") as lab:
        session = lab.create("thermal", seed=4)
        session.submit("wait", seconds=7)
        claimed = lab._claim("worker", models=("thermal",))
        branch = session.fork()
        assert branch.status()["time_s"] == 0
        lab._execute(claimed)
        assert session.status()["time_s"] == 7
        assert branch.status()["time_s"] == 0


def test_resubmitted_failure_joins_the_end_of_the_session_queue(tmp_path, monkeypatch):
    original = ThermalBench.perform

    def fail(model, state, rng, action, params):
        raise RuntimeError("Solver interrupted")

    with Lab(tmp_path / "retry.sqlite") as lab:
        session = lab.create("thermal", seed=3)
        session.submit("wait", seconds=1, operation_id="first")
        worker = Worker(lab)
        monkeypatch.setattr(ThermalBench, "perform", fail)
        assert worker.run_once()["status"] == "failed"
        monkeypatch.setattr(ThermalBench, "perform", original)
        session.submit("wait", seconds=2, operation_id="second")
        session.submit("wait", seconds=1, operation_id="first")
        assert worker.run_once()["operation_id"] == "second"
        assert worker.run_once()["operation_id"] == "first"
        assert [row["operation_id"] for row in session.history()] == ["second", "first"]
        assert session.status()["time_s"] == 3


def test_existing_results_survive_upgrade_and_public_description_is_retained(tmp_path):
    database = tmp_path / "existing.sqlite"
    with Lab(database) as lab:
        session = lab.create("thermal", seed=3)
        result = session.act("wait", seconds=7, operation_id="old")
        identifier = session.id
    with sqlite3.connect(database) as connection:
        old = connection.execute(
            "SELECT session,id,revision,request,result FROM operations"
        ).fetchall()
        connection.executescript("""
            DROP TABLE operations;
            DROP TABLE session_interfaces;
            DROP TABLE artifacts;
            CREATE TABLE operations (
                session TEXT NOT NULL REFERENCES sessions(id), id TEXT NOT NULL,
                revision INTEGER NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(session,id), UNIQUE(session,revision)
            );
            PRAGMA user_version=1;
        """)
        connection.executemany("INSERT INTO operations VALUES (?,?,?,?,?)", old)
    with Lab(database) as lab:
        assert lab.operation(identifier, "old")["result"] == result
        assert lab.describe_session(identifier)["name"] == "thermal"
        assert lab.status(identifier)["time_s"] == 7
        lab.session(identifier).act("wait", seconds=3)
        assert lab.status(identifier)["time_s"] == 10
        assert len(lab.session(identifier).history()) == 2
