PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    model_version TEXT NOT NULL,
    config TEXT NOT NULL,
    seed INTEGER NOT NULL,
    lineage TEXT NOT NULL,
    parent TEXT,
    parent_revision INTEGER,
    revision INTEGER NOT NULL,
    state TEXT NOT NULL,
    rng TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    session TEXT NOT NULL REFERENCES sessions(id),
    revision INTEGER NOT NULL,
    state TEXT NOT NULL,
    rng TEXT NOT NULL,
    PRIMARY KEY (session, revision)
);

CREATE TABLE IF NOT EXISTS operations (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL REFERENCES sessions(id),
    id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
    expected_revision INTEGER,
    base_revision INTEGER,
    revision INTEGER,
    request TEXT NOT NULL,
    result TEXT,
    error TEXT,
    worker TEXT,
    claim_until REAL,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    UNIQUE (session, id),
    UNIQUE (session, revision)
);

CREATE INDEX IF NOT EXISTS operations_status_sequence
    ON operations (status, sequence);

CREATE TABLE IF NOT EXISTS profiles (
    session TEXT PRIMARY KEY REFERENCES sessions(id),
    provenance TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    session TEXT NOT NULL REFERENCES sessions(id),
    operation_id TEXT,
    role TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    media_type TEXT NOT NULL,
    encoding TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS artifacts_session
    ON artifacts (session);

PRAGMA user_version = 3;
