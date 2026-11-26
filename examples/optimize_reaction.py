"""Compare temperature programmes for a selective consecutive reaction."""

import argparse
import json
from pathlib import Path

from synthetic_lab import Lab

SCHEDULES = {
    "steady": [(335.0, 1200.0)],
    "two-stage": [(365.0, 600.0), (325.0, 600.0)],
    "heat-then-quench": [(420.0, 120.0), (320.0, 1080.0)],
}


def run_schedule(root, schedule):
    experiment = root.fork()
    temperatures = []
    for setpoint, duration in schedule:
        experiment.act("set_temperature", setpoint=setpoint)
        experiment.act("wait", seconds=duration)
        temperatures.append(
            experiment.act("read", instrument="thermometer")["observations"][
                "temperature"
            ]["value"]
        )
    observations = experiment.act("read", instrument="chromatograph")["observations"]
    return experiment, {
        "schedule": schedule,
        "measured_temperatures_k": temperatures,
        "a_mol_per_l": observations["a"]["value"],
        "b_mol_per_l": observations["b"]["value"],
        "c_mol_per_l": observations["c"]["value"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runs/reaction-search.sqlite")
    parser.add_argument("--report", default="runs/reaction-search.json")
    args = parser.parse_args()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    with Lab(args.db) as lab:
        root = lab.create("reaction", seed=13)
        results = {}
        sessions = {}
        for name, schedule in SCHEDULES.items():
            experiment, result = run_schedule(root, schedule)
            results[name] = result
            sessions[name] = experiment.id
        winner = max(results, key=lambda name: results[name]["b_mol_per_l"])
        report = {
            "source": "simulation",
            "comparison": "common initial specimen and equal nominal process time",
            "objective": "maximize measured intermediate B concentration",
            "winner": winner,
            "sessions": sessions,
            "results": results,
        }
        Path(args.report).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
