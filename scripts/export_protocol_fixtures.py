"""Export live laboratory descriptions and observations for the language bindings."""

import argparse
import itertools
import json
from pathlib import Path

from synthetic_lab import Lab


def export():
    records = []
    with Lab(":memory:") as lab:
        for description in lab.catalogue():
            records.append({"laboratory": description})
            session = lab.create(description["name"], seed=7)
            fields = description["actions"]["read"]
            choices = [field.get("enum", [field.get("minimum")]) for field in fields.values()]
            for values in itertools.product(*choices):
                records.append({"result": session.act("read", **dict(zip(fields, values)))})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = export()
    args.output.write_text(json.dumps(records, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Exported {len(records)} live protocol records")
