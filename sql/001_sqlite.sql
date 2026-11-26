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
    session TEXT NOT NULL REFERENCES sessions(id),
    id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    request TEXT NOT NULL,
    result TEXT NOT NULL,
    PRIMARY KEY (session, id),
    UNIQUE (session, revision)
);

CREATE TABLE IF NOT EXISTS profiles (
    session TEXT PRIMARY KEY REFERENCES sessions(id),
    provenance TEXT NOT NULL
);

PRAGMA user_version = 1;
