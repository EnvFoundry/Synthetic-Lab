"""Continue one cell through a pulse and relaxation measurement."""

import json

from synthetic_lab import Lab


def main():
    with Lab("runs/battery.sqlite") as lab:
        cell = lab.create("battery", seed=7)
        rested = cell.act("read")
        cell.act("load", current=1.0)
        cell.act("wait", seconds=90)
        loaded = cell.act("read")
        cell.act("load", current=0.0)
        cell.act("wait", seconds=180)
        recovered = cell.act("read")
        cell.export(f"runs/{cell.id}.jsonl")
        print(
            json.dumps(
                {
                    "session": cell.id,
                    "source": "simulation",
                    "rested_v": rested["observations"]["voltage"]["value"],
                    "loaded_v": loaded["observations"]["voltage"]["value"],
                    "recovered_v": recovered["observations"]["voltage"]["value"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
