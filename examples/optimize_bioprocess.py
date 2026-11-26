"""Compare optical induction schedules in one fed-batch culture."""

import argparse
import json
from pathlib import Path

from synthetic_lab import Lab

SCHEDULES = {
    "early": [(1.0, 14400.0)],
    "delayed": [(0.0, 7200.0), (1.0, 7200.0)],
    "pulsed": [(1.0, 3600.0), (0.0, 3600.0), (1.0, 3600.0), (0.0, 3600.0)],
    "dark": [(0.0, 14400.0)],
}


def measure(session):
    od = session.act("read", instrument="od600")["observations"]["od600"]["value"]
    fluorescence = session.act("read", instrument="fluorescence")["observations"][
        "reporter_fluorescence"
    ]["value"]
    oxygen = session.act("read", instrument="optode")["observations"]["dissolved_oxygen"]["value"]
    raman = session.act("read", instrument="raman")["observations"]["raman_intensity"]["value"]
    return {
        "od600": od,
        "reporter_fluorescence_count_per_s": fluorescence,
        "dissolved_oxygen_percent": oxygen,
        "raman_intensity": raman,
        "product_sensitive_raman_score": raman[3] - 0.10 * raman[0],
    }


def run_schedule(root, schedule):
    experiment = root.fork()
    for level, duration in schedule:
        experiment.act("induction", level=level)
        experiment.act("wait", seconds=duration)
    return experiment, measure(experiment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runs/bioprocess.sqlite")
    parser.add_argument("--report", default="runs/bioprocess.json")
    args = parser.parse_args()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    with Lab(args.db) as lab:
        root = lab.create("spectroscopic-bioreactor", seed=41)
        root.act("feed", rate=0.05)
        root.act("aeration", kla=30.0)
        root.act("temperature", setpoint=310.15)
        root.act("wait", seconds=7200.0)

        results = {}
        sessions = {}
        for name, schedule in SCHEDULES.items():
            experiment, result = run_schedule(root, schedule)
            results[name] = result
            sessions[name] = experiment.id

        winner = max(
            results,
            key=lambda name: results[name]["product_sensitive_raman_score"],
        )
        report = {
            "source": "simulation",
            "comparison": "common culture state after two hours of pre-growth",
            "objective": "maximize a product-sensitive Raman contrast from public measurements",
            "winner": winner,
            "sessions": sessions,
            "results": results,
        }
        Path(args.report).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
