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
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_history_iterator_reads_in_batches(tmp_path):
    with Lab(tmp_path / "lab.sqlite") as lab:
        session = lab.create("thermal", seed=6)
        for index in range(7):
            session.act("wait", seconds=1, operation_id=f"step-{index}")
        records = list(lab.iter_history(session.id, batch_size=2))
        assert [record["revision"] for record in records] == list(range(1, 8))
