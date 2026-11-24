import sqlite3

from synthetic_lab import Lab


def test_calibration_reference_follows_new_sessions_and_branches(tmp_path):
    database = tmp_path / "profiles.sqlite"
    provenance = {
        "source": "measurement",
        "reference": "fixture-data-v3.jsonl",
        "method": "steady-state regression",
        "valid_power_range_w": [0, 0.8],
    }
    with Lab(database) as lab:
        experiment = lab.create(
            "thermal", config={"thermal_resistance": 9, "variation": 0}, provenance=provenance
        )
        result = experiment.act("read")
        assert result["source"] == "simulation"
        assert result["model_provenance"] == provenance
        identifier = experiment.fork().id
    with Lab(database) as lab:
        assert lab.status(identifier)["model_provenance"] == provenance


def test_existing_schema_without_profiles_remains_readable(tmp_path):
    database = tmp_path / "older.sqlite"
    with Lab(database) as lab:
        identifier = lab.create("thermal", seed=1).id
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE profiles")
    with Lab(database) as lab:
        assert lab.status(identifier)["model_provenance"] == {"source": "theory"}
        assert lab.session(identifier).act("read")["source"] == "simulation"
