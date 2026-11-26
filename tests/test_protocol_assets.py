import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_protocol_schema_and_fixture_are_versioned_json():
    schema = json.loads((ROOT / "spec/synthetic-lab.schema.json").read_text())
    fixture = json.loads((ROOT / "spec/examples/operation-result.json").read_text())
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$defs"]["operationResult"]["properties"]["schema_version"] == {
        "const": 1
    }
    assert fixture["schema_version"] == 1
    assert fixture["end_s"] >= fixture["start_s"]


def test_sqlite_migration_creates_runtime_tables():
    script = (ROOT / "sql/001_sqlite.sql").read_text()
    with sqlite3.connect(":memory:") as database:
        database.executescript(script)
        tables = {
            row[0]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }
        assert {"operations", "profiles", "sessions", "snapshots"} <= tables
        assert database.execute("PRAGMA user_version").fetchone()[0] == 1
