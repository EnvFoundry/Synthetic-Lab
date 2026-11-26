"""Durable simulation sessions with short database transactions and external workers."""

import copy
import json
import random
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .model import arguments
from .models import available, load


class Conflict(ValueError):
    """A request disagrees with an existing operation or session revision."""


class OperationFailed(RuntimeError):
    """A queued operation finished with an exception."""

    def __init__(self, error):
        self.error = error
        super().__init__(f"{error.get('type', 'OperationError')}: {error.get('message', '')}")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def tuples(value):
    return tuple(map(tuples, value)) if isinstance(value, list) else value


class Lab:
    """A durable experiment database shared by clients and domain worker processes."""

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
        self._initialize()

    def _initialize(self):
        with self._transaction():
            schema = self._db.execute("PRAGMA user_version").fetchone()[0]
            if schema not in (0, 1, 2):
                raise ValueError(f"Unsupported database schema {schema}")
            self._db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, model TEXT NOT NULL, model_version TEXT NOT NULL,
                config TEXT NOT NULL, seed INTEGER NOT NULL, lineage TEXT NOT NULL,
                parent TEXT, parent_revision INTEGER, revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL)""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
                session TEXT NOT NULL REFERENCES sessions(id), revision INTEGER NOT NULL,
                state TEXT NOT NULL, rng TEXT NOT NULL, PRIMARY KEY(session, revision))""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS profiles (
                session TEXT PRIMARY KEY REFERENCES sessions(id), provenance TEXT NOT NULL)""")
            if schema == 1:
                self._db.execute("ALTER TABLE operations RENAME TO operations_v1")
            if schema in (0, 1):
                self._db.execute("""CREATE TABLE operations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    session TEXT NOT NULL REFERENCES sessions(id), id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending', 'running', 'succeeded', 'failed')
                    ), expected_revision INTEGER, base_revision INTEGER,
                    revision INTEGER, request TEXT NOT NULL, result TEXT, error TEXT,
                    worker TEXT, claim_until REAL, created REAL NOT NULL, updated REAL NOT NULL,
                    UNIQUE(session, id), UNIQUE(session, revision))""")
                self._db.execute(
                    "CREATE INDEX operations_status_sequence ON operations(status, sequence)"
                )
                if schema == 1:
                    now = time.time()
                    self._db.execute(
                        """INSERT INTO operations (
                            session, id, status, base_revision, revision, request, result,
                            created, updated)
                        SELECT session, id, 'succeeded', revision - 1, revision, request, result,
                               ?, ? FROM operations_v1""",
                        (now, now),
                    )
                    self._db.execute("DROP TABLE operations_v1")
                self._db.execute("PRAGMA user_version = 2")

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

    @staticmethod
    def _expected_revision(value):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError("expected_revision must be a nonnegative integer")
        return value

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
                    "SELECT id, model, model_version, revision, lineage "
                    "FROM sessions ORDER BY rowid"
                )
            ]

    @staticmethod
    def _operation_view(row):
        result = {
            "session": row["session"],
            "operation_id": row["id"],
            "status": row["status"],
        }
        if row["revision"] is not None:
            result["revision"] = row["revision"]
        if row["result"] is not None:
            result["result"] = json.loads(row["result"])
        if row["error"] is not None:
            result["error"] = json.loads(row["error"])
        return result

    def operation(self, session_id, operation_id):
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM operations WHERE session = ? AND id = ?",
                (session_id, operation_id),
            ).fetchone()
            if row is None:
                raise ValueError(f"Unknown operation {operation_id!r} for session {session_id!r}")
            return self._operation_view(row)

    def submit(self, session_id, action, params, *, operation_id=None, expected_revision=None):
        operation_id = self._identifier(operation_id)
        expected_revision = self._expected_revision(expected_revision)
        with self._lock:
            row = self._row(session_id)
            model = self._model(row)
            if action not in model.actions:
                raise ValueError(f"Unknown action {action!r}; choose from {sorted(model.actions)}")
            parsed = arguments(params, model.actions[action])
        request = encode({"action": action, "parameters": parsed})
        now = time.time()
        with self._transaction():
            session = self._row(session_id)
            previous = self._db.execute(
                "SELECT * FROM operations WHERE session = ? AND id = ?",
                (session_id, operation_id),
            ).fetchone()
            if previous is not None:
                if previous["request"] != request:
                    raise Conflict("Operation identifier already used for different parameters")
                if previous["status"] == "failed":
                    self._db.execute(
                        """UPDATE operations SET status = 'pending', expected_revision = ?,
                           base_revision = NULL, revision = NULL, result = NULL, error = NULL,
                           worker = NULL, claim_until = NULL, updated = ?
                           WHERE sequence = ?""",
                        (expected_revision, now, previous["sequence"]),
                    )
                    previous = self._db.execute(
                        "SELECT * FROM operations WHERE sequence = ?",
                        (previous["sequence"],),
                    ).fetchone()
                return self._operation_view(previous)
            if expected_revision is not None and expected_revision != session["revision"]:
                raise Conflict(
                    f"Expected revision {expected_revision}, found {session['revision']}"
                )
            self._db.execute(
                """INSERT INTO operations (
                    session, id, status, expected_revision, request, created, updated)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?)""",
                (session_id, operation_id, expected_revision, request, now, now),
            )
            row = self._db.execute(
                "SELECT * FROM operations WHERE session = ? AND id = ?",
                (session_id, operation_id),
            ).fetchone()
            return self._operation_view(row)

    def _claim(self, worker_id, *, models=None, session_id=None, operation_id=None, lease=300.0):
        if lease <= 0:
            raise ValueError("lease must be positive")
        supported = tuple(available() if models is None else models)
        if not supported:
            return None
        now = time.time()
        conditions = [
            "(o.status = 'pending' OR (o.status = 'running' AND o.claim_until < ?))",
            "NOT EXISTS (SELECT 1 FROM operations earlier WHERE earlier.session = o.session "
            "AND earlier.sequence < o.sequence AND earlier.status IN ('pending', 'running'))",
            f"s.model IN ({','.join('?' for _ in supported)})",
        ]
        parameters = [now, *supported]
        if session_id is not None:
            conditions.append("o.session = ?")
            parameters.append(session_id)
        if operation_id is not None:
            conditions.append("o.id = ?")
            parameters.append(operation_id)
        query = f"""SELECT o.*, s.model, s.model_version, s.config, s.lineage,
                           s.revision AS session_revision, s.state, s.rng,
                           COALESCE(p.provenance, '{{\"source\":\"theory\"}}') AS provenance
                    FROM operations o
                    JOIN sessions s ON s.id = o.session
                    LEFT JOIN profiles p ON p.session = o.session
                    WHERE {' AND '.join(conditions)}
                    ORDER BY o.sequence LIMIT 1"""
        with self._transaction():
            row = self._db.execute(query, parameters).fetchone()
            if row is None:
                return None
            if (
                row["expected_revision"] is not None
                and row["expected_revision"] != row["session_revision"]
            ):
                error = {
                    "type": "Conflict",
                    "message": (
                        f"Expected revision {row['expected_revision']}, "
                        f"found {row['session_revision']}"
                    ),
                }
                self._db.execute(
                    """UPDATE operations SET status = 'failed', error = ?, worker = NULL,
                       claim_until = NULL, updated = ? WHERE sequence = ?""",
                    (encode(error), now, row["sequence"]),
                )
                return {"failed": self.operation(row["session"], row["id"])}
            self._db.execute(
                """UPDATE operations SET status = 'running', base_revision = ?, worker = ?,
                   claim_until = ?, updated = ? WHERE sequence = ?""",
                (
                    row["session_revision"],
                    worker_id,
                    now + lease,
                    now,
                    row["sequence"],
                ),
            )
            return {
                "sequence": row["sequence"],
                "session": row["session"],
                "operation_id": row["id"],
                "worker": worker_id,
                "lease": lease,
                "base_revision": row["session_revision"],
                "model": row["model"],
                "model_version": row["model_version"],
                "config": row["config"],
                "lineage": row["lineage"],
                "state": row["state"],
                "rng": row["rng"],
                "request": row["request"],
                "provenance": row["provenance"],
            }

    def _extend_claim(self, task):
        now = time.time()
        with self._transaction():
            self._db.execute(
                """UPDATE operations SET claim_until = ?, updated = ?
                   WHERE sequence = ? AND status = 'running' AND worker = ?""",
                (now + task["lease"], now, task["sequence"], task["worker"]),
            )

    def _fail_task(self, task, error):
        now = time.time()
        with self._transaction():
            self._db.execute(
                """UPDATE operations SET status = 'failed', error = ?, worker = NULL,
                   claim_until = NULL, updated = ?
                   WHERE sequence = ? AND status = 'running' AND worker = ?""",
                (encode(error), now, task["sequence"], task["worker"]),
            )

    def _complete_task(self, task, state, rng, result):
        now = time.time()
        result_json = encode(result)
        revision = task["base_revision"] + 1
        with self._transaction():
            operation = self._db.execute(
                "SELECT status, worker FROM operations WHERE sequence = ?", (task["sequence"],)
            ).fetchone()
            if (
                operation is None
                or operation["status"] != "running"
                or operation["worker"] != task["worker"]
            ):
                raise Conflict("Operation is no longer owned by this worker")
            row = self._row(task["session"])
            if row["revision"] != task["base_revision"]:
                raise Conflict(
                    f"Operation began at revision {task['base_revision']}, found {row['revision']}"
                )
            self._db.execute(
                "UPDATE sessions SET state = ?, rng = ?, revision = ? WHERE id = ?",
                (encode(state), encode(rng.getstate()), revision, task["session"]),
            )
            self._db.execute(
                """UPDATE operations SET status = 'succeeded', revision = ?, result = ?,
                   error = NULL, worker = NULL, claim_until = NULL, updated = ?
                   WHERE sequence = ?""",
                (revision, result_json, now, task["sequence"]),
            )
            self._snapshot(task["session"], revision, state, rng)
        return result

    def _execute(self, task):
        stop = threading.Event()

        def heartbeat():
            interval = max(0.1, task["lease"] / 3.0)
            while not stop.wait(interval):
                self._extend_claim(task)

        pulse = threading.Thread(target=heartbeat, daemon=True)
        pulse.start()
        try:
            model = load(task["model"], json.loads(task["config"]))
            if model.version != task["model_version"]:
                raise Conflict(
                    f"Session needs {task['model']} model version {task['model_version']}"
                )
            request = json.loads(task["request"])
            state = json.loads(task["state"])
            rng = random.Random()
            rng.setstate(tuples(json.loads(task["rng"])))
            start = state["time_s"]
            observations = model.perform(
                state, rng, request["action"], request["parameters"]
            )
            if state["time_s"] < start:
                raise ValueError("A model cannot move experiment time backwards")
            result = {
                "schema_version": 1,
                "session": task["session"],
                "lineage": task["lineage"],
                "operation_id": task["operation_id"],
                "revision": task["base_revision"] + 1,
                "model": task["model"],
                "model_version": model.version,
                "source": "simulation",
                "model_provenance": json.loads(task["provenance"]),
                "action": request["action"],
                "parameters": request["parameters"],
                "start_s": start,
                "end_s": state["time_s"],
                "observations": observations,
                "configuration": model.visible(state),
            }
            return self._complete_task(task, state, rng, result)
        except BaseException as exc:
            self._fail_task(task, {"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            stop.set()
            pulse.join(timeout=1.0)

    def run_next(self, *, worker_id=None, models=None, session_id=None, lease=300.0):
        worker_id = self._identifier(worker_id)
        claimed = self._claim(
            worker_id, models=models, session_id=session_id, lease=lease
        )
        if claimed is None:
            return None
        if "failed" in claimed:
            return claimed["failed"]
        try:
            self._execute(claimed)
        except Exception:
            pass
        return self.operation(claimed["session"], claimed["operation_id"])

    def wait_operation(self, session_id, operation_id, *, timeout=None, poll=0.02):
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be nonnegative")
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            current = self.operation(session_id, operation_id)
            if current["status"] in ("succeeded", "failed"):
                return current
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"Operation {operation_id!r} did not finish")
            time.sleep(poll)

    def act(self, session_id, action, params, *, operation_id=None, expected_revision=None):
        submitted = self.submit(
            session_id,
            action,
            params,
            operation_id=operation_id,
            expected_revision=expected_revision,
        )
        operation_id = submitted["operation_id"]
        if submitted["status"] == "succeeded":
            return submitted["result"]
        with self._lock:
            model_name = self._row(session_id)["model"]
        while True:
            current = self.operation(session_id, operation_id)
            if current["status"] == "succeeded":
                return current["result"]
            if current["status"] == "failed":
                raise OperationFailed(current["error"])
            claimed = self._claim(
                "local-" + uuid.uuid4().hex,
                models=(model_name,),
                session_id=session_id,
                operation_id=operation_id,
            )
            if claimed is not None:
                if "failed" in claimed:
                    raise OperationFailed(claimed["failed"]["error"])
                return self._execute(claimed)
            earlier = self.run_next(models=(model_name,), session_id=session_id)
            if earlier is None:
                time.sleep(0.01)

    def fork(self, session_id, *, at_revision=None, session_id_new=None):
        identifier = self._identifier(session_id_new)
        with self._transaction():
            row = self._row(session_id)
            self._model(row)
            active = self._db.execute(
                """SELECT 1 FROM operations WHERE session = ?
                   AND status IN ('pending', 'running') LIMIT 1""",
                (session_id,),
            ).fetchone()
            if active is not None:
                raise Conflict("Finish queued operations before forking this session")
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

    def iter_history(self, session_id, *, after=0, batch_size=100):
        if isinstance(after, bool) or not isinstance(after, int) or after < 0:
            raise ValueError("after must be a nonnegative integer")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        with self._lock:
            self._row(session_id)
        cursor = after
        while True:
            with self._lock:
                rows = self._db.execute(
                    """SELECT revision, result FROM operations
                       WHERE session = ? AND status = 'succeeded' AND revision > ?
                       ORDER BY revision LIMIT ?""",
                    (session_id, cursor, batch_size),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                cursor = row["revision"]
                yield json.loads(row["result"])

    def history(self, session_id, *, after=0):
        return list(self.iter_history(session_id, after=after))

    def export(self, session_id, path):
        """Write observable operations incrementally without loading full history."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        count = 0
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                for record in self.iter_history(session_id):
                    stream.write(encode(record) + "\n")
                    count += 1
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return count


class Session:
    def __init__(self, lab, session_id):
        self.lab = lab
        self.id = session_id

    def act(self, action, *, operation_id=None, expected_revision=None, **params):
        return self.lab.act(
            self.id, action, params, operation_id=operation_id, expected_revision=expected_revision
        )

    def submit(self, action, *, operation_id=None, expected_revision=None, **params):
        return self.lab.submit(
            self.id, action, params, operation_id=operation_id, expected_revision=expected_revision
        )

    def operation(self, operation_id):
        return self.lab.operation(self.id, operation_id)

    def status(self):
        return copy.deepcopy(self.lab.status(self.id))

    def fork(self, *, at_revision=None, session_id=None):
        return self.lab.fork(self.id, at_revision=at_revision, session_id_new=session_id)

    def history(self, *, after=0):
        return self.lab.history(self.id, after=after)

    def export(self, path):
        return self.lab.export(self.id, path)
