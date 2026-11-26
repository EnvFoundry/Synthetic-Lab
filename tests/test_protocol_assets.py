import json
import sqlite3
from pathlib import Path

from jsonschema import Draft202012Validator

from synthetic_lab import Lab

ROOT = Path(__file__).parents[1]


def test_protocol_schema_and_fixture_are_versioned_json():
    schema = json.loads((ROOT / "spec/synthetic-lab.schema.json").read_text())
    fixture = json.loads((ROOT / "spec/examples/operation-result.json").read_text())
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$defs"]["operationResult"]["properties"]["schema_version"] == {"const": 1}
    assert fixture["schema_version"] == 1
    assert fixture["end_s"] >= fixture["start_s"]
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate({"result": fixture})


def test_live_catalogue_and_all_instrument_results_follow_schema():
    import runpy

    exporter = runpy.run_path(str(ROOT / "scripts/export_protocol_fixtures.py"))
    validator = Draft202012Validator(
        json.loads((ROOT / "spec/synthetic-lab.schema.json").read_text())
    )
    records = exporter["export"]()
    for record in records:
        validator.validate(record)
        if "laboratory" in record:
            description = record["laboratory"]
            contract = description["research_contract"]
            assert set(contract["action_semantics"]) == set(description["actions"])
        else:
            result = record["result"]
            assert result["end_s"] >= result["start_s"]


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


def test_runtime_opens_a_database_created_from_sql(tmp_path):
    path = tmp_path / "lab.sqlite"
    with sqlite3.connect(path) as database:
        database.executescript((ROOT / "sql/001_sqlite.sql").read_text())
    with Lab(path) as lab:
        experiment = lab.create("reaction", seed=3)
        first = experiment.act("read", instrument="spectrometer", operation_id="spectrum")
    with Lab(path) as lab:
        resumed = lab.session(experiment.id)
        assert resumed.act("read", instrument="spectrometer", operation_id="spectrum") == first
