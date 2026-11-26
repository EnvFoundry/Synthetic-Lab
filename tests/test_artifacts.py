import json
import sqlite3

import pytest

import synthetic_lab.runtime as runtime_module
from synthetic_lab import Lab
from synthetic_lab.model import Parameter


class LargeModel:
    name = "large-json"
    version = "1"
    description = "Exercise external state and observation storage."
    defaults = {}
    actions = {
        "noop": {},
        "mutate": {"delta": Parameter(None, -10, 10)},
        "read": {},
    }

    def __init__(self, config=None):
        self.config = {}

    def initial(self, rng):
        return {
            "time_s": 0.0,
            "field": [[row * 100 + column for column in range(32)] for row in range(32)],
            "steps": 0,
        }

    def perform(self, state, rng, action, params):
        if action == "noop":
            state["time_s"] += 1.0
        elif action == "mutate":
            state["field"][0][0] += params["delta"]
            state["steps"] += 1
            state["time_s"] += 1.0
        elif action == "read":
            state["time_s"] += 0.1
            return {
                "field": {
                    "value": state["field"],
                    "unit": "a.u.",
                    "shape": [32, 32],
                    "axes": ["row", "column"],
                }
            }
        return {}

    def visible(self, state):
        return {"steps": state["steps"], "first": state["field"][0][0]}

    def describe(self):
        return {"name": self.name, "actions": {name: {} for name in self.actions}}


@pytest.fixture
def large_model(monkeypatch):
    original_load = runtime_module.load
    original_available = runtime_module.available

    def load(name, config=None):
        if name == LargeModel.name:
            return LargeModel(config)
        return original_load(name, config)

    monkeypatch.setattr(runtime_module, "load", load)
    monkeypatch.setattr(
        runtime_module,
        "available",
        lambda: sorted({*original_available(), LargeModel.name}),
    )


def artifact_id(reference):
    return reference["$artifact"]["id"]


def packed_state(lab, session_id):
    row = lab._db.execute("SELECT state FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return json.loads(row["state"])


def test_large_state_and_observation_are_external_and_streamable(tmp_path, large_model):
    database = tmp_path / "lab.sqlite"
    with Lab(database, artifact_threshold=256) as lab:
        session = lab.create(LargeModel.name, seed=3)
        initial_reference = packed_state(lab, session.id)["field"]
        initial_id = artifact_id(initial_reference)
        initial_value = lab.read_artifact(initial_id)
        assert len(initial_value) == 32
        assert lab.artifact_info(initial_id)["role"] == "state"

        session.act("noop", operation_id="noop")
        assert artifact_id(packed_state(lab, session.id)["field"]) == initial_id
        state_count = lab._db.execute(
            "SELECT count(*) FROM artifacts WHERE role = 'state'"
        ).fetchone()[0]
        assert state_count == 1

        result = session.act("read", operation_id="image")
        observation_reference = result["observations"]["field"]["value"]
        observation_id = artifact_id(observation_reference)
        assert lab.read_artifact(observation_id) == initial_value
        raw_result = lab._db.execute("SELECT result FROM operations WHERE id = 'image'").fetchone()[
            0
        ]
        assert len(raw_result) < len(json.dumps(initial_value))

        chunks = b"".join(lab.iter_artifact(observation_id, chunk_size=37))
        assert json.loads(chunks) == initial_value
        destination = tmp_path / "field.json"
        exported = lab.export_artifact(observation_id, destination)
        assert exported["path"] == str(destination)
        assert json.loads(destination.read_text()) == initial_value

        trace = tmp_path / "trace.jsonl"
        session.export(trace)
        records = [json.loads(line) for line in trace.read_text().splitlines()]
        assert artifact_id(records[1]["observations"]["field"]["value"]) == observation_id

        branch = session.fork()
        assert branch.status()["configuration"]["first"] == 0

        session.act("mutate", delta=5, operation_id="mutate")
        changed_id = artifact_id(packed_state(lab, session.id)["field"])
        assert changed_id != initial_id
        assert session.status()["configuration"] == {"steps": 1, "first": 5}
        session_id = session.id

    with Lab(database, artifact_threshold=256) as lab:
        resumed = lab.session(session_id)
        assert resumed.status()["configuration"] == {"steps": 1, "first": 5}
        resumed.act("noop", operation_id="resumed-noop")
        state_count = lab._db.execute(
            "SELECT count(*) FROM artifacts WHERE role = 'state'"
        ).fetchone()[0]
        assert state_count == 2


def test_schema_two_database_adds_external_artifact_metadata(tmp_path):
    database = tmp_path / "schema-two.sqlite"
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
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT NOT NULL REFERENCES sessions(id), id TEXT NOT NULL,
                status TEXT NOT NULL, expected_revision INTEGER, base_revision INTEGER,
                revision INTEGER, request TEXT NOT NULL, result TEXT, error TEXT,
                worker TEXT, claim_until REAL, created REAL NOT NULL, updated REAL NOT NULL,
                UNIQUE(session, id), UNIQUE(session, revision)
            );
            CREATE TABLE profiles (
                session TEXT PRIMARY KEY REFERENCES sessions(id), provenance TEXT NOT NULL
            );
            PRAGMA user_version = 2;
            """
        )
    with Lab(database):
        pass
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "artifacts" in tables
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
