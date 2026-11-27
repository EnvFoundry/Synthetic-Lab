"""Export live laboratory descriptions and observations for the language bindings."""

import argparse
import itertools
import json
from pathlib import Path

from synthetic_lab import Lab


def export(initial_reads=()):
    records = []
    with Lab(":memory:", artifact_threshold=512) as lab:
        catalogue = lab.catalogue()
        unknown = set(initial_reads) - {item["name"] for item in catalogue}
        if unknown:
            raise ValueError(f"Initial-read laboratories are not installed: {sorted(unknown)}")
        for description in catalogue:
            records.append({"laboratory": description})
            # A catalogue entry does not imply a fresh specimen can already be measured.
            # Executable fixtures explicitly name laboratories with initial readouts.
            if description["name"] not in initial_reads:
                continue
            session = lab.create(description["name"], seed=7)
            fields = description["actions"]["read"]
            choices = [field.get("enum", [field.get("minimum")]) for field in fields.values()]
            for values in itertools.product(*choices):
                records.append({"result": session.act("read", **dict(zip(fields, values)))})
            if description["actions"].get("trace") == {}:
                records.append({"result": session.act("trace")})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--initial-read",
        action="append",
        default=[],
        metavar="MODEL",
        help="Also acquire initial readouts from this laboratory (repeatable)",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = export(args.initial_read)
    args.output.write_text(json.dumps(records, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Exported {len(records)} live protocol records")
