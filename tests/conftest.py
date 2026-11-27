import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


@pytest.fixture
def assert_protocol_result():
    schema = Path(__file__).parents[1] / "spec/synthetic-lab.schema.json"
    validator = Draft202012Validator(json.loads(schema.read_text()))
    return lambda result: validator.validate({"result": result})
