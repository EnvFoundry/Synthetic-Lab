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
    start = experiment.status()["time_s"]
    deadline = start
    for setpoint, duration in schedule:
        deadline += duration
        experiment.act("set_temperature", setpoint=setpoint)
        # Include the command and thermometer acquisition in each stage's budget.
        remaining = deadline - experiment.status()["time_s"] - 0.2
        if remaining < 0:
            raise ValueError("Temperature stages must leave time for a thermometer reading")
        experiment.act("wait", seconds=remaining)
        temperatures.append(
            experiment.act("read", instrument="thermometer")["observations"]["temperature"]["value"]
        )
    observations = experiment.act("read", instrument="chromatograph")["observations"]
    return experiment, {
        "schedule": schedule,
        "elapsed_s": experiment.status()["time_s"] - start,
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
            "comparison": "common initial specimen and equal elapsed time including measurements",
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
