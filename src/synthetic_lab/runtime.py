"""Atomic local simulation sessions. Real instruments remain owned by IOP."""

import copy
import json
import random
import secrets
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from .model import arguments
from .models import available, load


class Conflict(ValueError):
    """A request disagrees with an existing operation or session revision."""


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def tuples(value):
    return tuple(map(tuples, value)) if isinstance(value, list) else value


class Lab:
    """One SQLite database. Use one Lab per worker process; a Lab is thread-safe."""

    def __init__(self, database="synthetic-lab.sqlite"):
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.database = str(Path(self.database).expanduser().resolve())
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            self.database, timeout=30, isolation_level=None, check_same_thread=False
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")
        with self._transaction():
            schema = self._db.execute("PRAGMA user_version").fetchone()[0]
            if schema not in (0, 1):
                raise ValueError(f"Unsupported database schema {schema}")
            self._db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, model TEXT NOT NULL, model_version TEXT NOT NULL,
                config TEXT NOT NULL, seed INTEGER NOT NULL, lineage TEXT NOT NULL,
                parent TEXT, parent_revision INTEGER, revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL)""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
                session TEXT NOT NULL REFERENCES sessions(id), revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL, PRIMARY KEY(session, revision))""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS operations (
                session TEXT NOT NULL REFERENCES sessions(id), id TEXT NOT NULL,
                revision INTEGER NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(session, id), UNIQUE(session, revision))""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS profiles (
                session TEXT PRIMARY KEY REFERENCES sessions(id), provenance TEXT NOT NULL)""")
            self._db.execute("PRAGMA user_version = 1")

    @contextmanager
    def _transaction(self):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def close(self):
        with self._lock:
            self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @staticmethod
    def catalogue():
        return [load(name).describe() for name in available()]

    def _row(self, session_id):
        row = self._db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown session {session_id!r}")
        return row

    @staticmethod
    def _model(row):
        model = load(row["model"], json.loads(row["config"]))
        if model.version != row["model_version"]:
            raise Conflict(f"Session needs {row['model']} model version {row['model_version']}")
        return model

    def create(self, model, *, seed=None, config=None, session_id=None, provenance=None):
        implementation = load(model, config)
        provenance = {"source": "theory"} if provenance is None else provenance
        if not isinstance(provenance, dict) or provenance.get("source") not in (
            "theory",
            "measurement",
            "simulation",
        ):
            raise ValueError(
                "Profile provenance requires source = theory, measurement or simulation"
            )
        if provenance["source"] != "theory" and not provenance.get("reference"):
            raise ValueError("A calibrated profile requires a data reference")
        profile_json = encode(provenance)
        seed = secrets.randbits(63) if seed is None else seed
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
            raise ValueError("seed must be an integer in [0, 2**63)")
        session_id = self._identifier(session_id)
        rng = random.Random(seed)
        state = implementation.initial(rng)
        with self._transaction():
            try:
                self._db.execute(
                    "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        model,
                        implementation.version,
                        encode(implementation.config),
                        seed,
                        session_id,
                        None,
                        None,
                        0,
                        encode(state),
                        encode(rng.getstate()),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise Conflict(f"Session {session_id!r} already exists") from exc
            self._snapshot(session_id, 0, state, rng)
            self._db.execute("INSERT INTO profiles VALUES (?, ?)", (session_id, profile_json))
        return Session(self, session_id)

    @staticmethod
    def _identifier(identifier):
        identifier = uuid.uuid4().hex if identifier is None else identifier
        if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 200:
            raise ValueError("Identifiers must be nonempty strings of at most 200 characters")
        return identifier

    def session(self, session_id):
        with self._lock:
            self._model(self._row(session_id))
        return Session(self, session_id)

    def _snapshot(self, session_id, revision, state, rng):
        self._db.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, ?)",
            (session_id, revision, encode(state), encode(rng.getstate())),
        )

    def _provenance(self, session_id):
        row = self._db.execute(
            "SELECT provenance FROM profiles WHERE session = ?", (session_id,)
        ).fetchone()
        return json.loads(row[0]) if row else {"source": "theory"}

    def status(self, session_id):
        with self._lock:
            row = self._row(session_id)
            model = self._model(row)
            state = json.loads(row["state"])
            return {
                "session": row["id"],
                "model": row["model"],
                "model_version": row["model_version"],
                "revision": row["revision"],
                "lineage": row["lineage"],
                "parent": row["parent"],
                "parent_revision": row["parent_revision"],
                "time_s": state["time_s"],
                "source": "simulation",
                "model_provenance": self._provenance(session_id),
                "configuration": model.visible(state),
            }

    def list_sessions(self):
        with self._lock:
            return [
                dict(row)
                for row in self._db.execute(
                    "SELECT id, model, model_version, revision, lineage FROM sessions ORDER BY rowid"
                )
            ]

    def act(self, session_id, action, params, *, operation_id=None, expected_revision=None):
        operation_id = self._identifier(operation_id)
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ValueError("expected_revision must be a nonnegative integer")
        with self._transaction():
            row = self._row(session_id)
            model = self._model(row)
            if action not in model.actions:
                raise ValueError(f"Unknown action {action!r}; choose from {sorted(model.actions)}")
            parsed = arguments(params, model.actions[action])
            request = encode({"action": action, "parameters": parsed})
            previous = self._db.execute(
                "SELECT request, result FROM operations WHERE session = ? AND id = ?",
                (session_id, operation_id),
            ).fetchone()
            if previous:
                if previous["request"] != request:
                    raise Conflict("Operation identifier already used for different parameters")
                return json.loads(previous["result"])
            if expected_revision is not None and expected_revision != row["revision"]:
                raise Conflict(f"Expected revision {expected_revision}, found {row['revision']}")
            state = json.loads(row["state"])
            rng = random.Random()
            rng.setstate(tuples(json.loads(row["rng"])))
            start = state["time_s"]
            observations = model.perform(state, rng, action, parsed)
            if state["time_s"] < start:
                raise ValueError("A model cannot move experiment time backwards")
            revision = row["revision"] + 1
            result = {
                "schema_version": 1,
                "session": session_id,
                "lineage": row["lineage"],
                "operation_id": operation_id,
                "revision": revision,
                "model": row["model"],
                "model_version": model.version,
                "source": "simulation",
                "model_provenance": self._provenance(session_id),
                "action": action,
                "parameters": parsed,
                "start_s": start,
                "end_s": state["time_s"],
                "observations": observations,
                "configuration": model.visible(state),
            }
            result_json = encode(result)
            self._db.execute(
                "UPDATE sessions SET state = ?, rng = ?, revision = ? WHERE id = ?",
                (encode(state), encode(rng.getstate()), revision, session_id),
            )
            self._db.execute(
                "INSERT INTO operations VALUES (?, ?, ?, ?, ?)",
                (session_id, operation_id, revision, request, result_json),
            )
            self._snapshot(session_id, revision, state, rng)
        return result

    def fork(self, session_id, *, at_revision=None, session_id_new=None):
        identifier = self._identifier(session_id_new)
        with self._transaction():
            row = self._row(session_id)
            self._model(row)
            revision = row["revision"] if at_revision is None else at_revision
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
                raise ValueError("at_revision must be a nonnegative integer")
            snap = self._db.execute(
                "SELECT * FROM snapshots WHERE session = ? AND revision = ?", (session_id, revision)
            ).fetchone()
            if snap is None:
                raise ValueError(f"No snapshot at revision {revision}")
            try:
                self._db.execute(
                    "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        identifier,
                        row["model"],
                        row["model_version"],
                        row["config"],
                        row["seed"],
                        row["lineage"],
                        session_id,
                        revision,
                        0,
                        snap["state"],
                        snap["rng"],
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise Conflict(f"Session {identifier!r} already exists") from exc
            self._db.execute(
                "INSERT INTO snapshots VALUES (?, 0, ?, ?)",
                (identifier, snap["state"], snap["rng"]),
            )
            self._db.execute(
                "INSERT INTO profiles VALUES (?, ?)",
                (identifier, encode(self._provenance(session_id))),
            )
        return Session(self, identifier)

    def history(self, session_id, *, after=0):
        if isinstance(after, bool) or not isinstance(after, int) or after < 0:
            raise ValueError("after must be a nonnegative integer")
        with self._lock:
            self._row(session_id)
            return [
                json.loads(row[0])
                for row in self._db.execute(
                    "SELECT result FROM operations WHERE session = ? AND revision > ? ORDER BY revision",
                    (session_id, after),
                )
            ]

    def export(self, session_id, path):
        """Export observable actions and readings. Branch history starts at its fork."""
        records = self.history(session_id)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_text("".join(encode(row) + "\n" for row in records), encoding="utf-8")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return len(records)


class Session:
    def __init__(self, lab, session_id):
        self.lab = lab
        self.id = session_id

    def act(self, action, *, operation_id=None, expected_revision=None, **params):
        return self.lab.act(
            self.id, action, params, operation_id=operation_id, expected_revision=expected_revision
        )

    def status(self):
        return copy.deepcopy(self.lab.status(self.id))

    def fork(self, *, at_revision=None, session_id=None):
        return self.lab.fork(self.id, at_revision=at_revision, session_id_new=session_id)

    def history(self, *, after=0):
        return self.lab.history(self.id, after=after)

    def export(self, path):
        return self.lab.export(self.id, path)
