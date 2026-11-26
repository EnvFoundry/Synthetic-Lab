"""Compare deposition endpoints against a target optical spectrum."""

import argparse
import json
from pathlib import Path

from synthetic_lab import Lab

TARGET = [0.17726, 0.111834, 0.060422, 0.041969, 0.051471, 0.075676, 0.10392, 0.130394]
CANDIDATE_SECONDS = (120.0, 180.0, 240.0)


def spectrum(session):
    return session.act("read", instrument="reflectometer")["observations"]["reflectance"][
        "value"
    ]


def loss(values):
    return sum((measured - target) ** 2 for measured, target in zip(values, TARGET))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runs/thin-film.sqlite")
    parser.add_argument("--report", default="runs/thin-film.json")
    args = parser.parse_args()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    with Lab(args.db) as lab:
        root = lab.create("thin-film", seed=29)
        candidates = {}
        for seconds in CANDIDATE_SECONDS:
            experiment = root.fork()
            experiment.act("deposition", rate=0.8)
            experiment.act("shutter", position="open")
            experiment.act("wait", seconds=seconds)
            experiment.act("shutter", position="closed")
            measured = spectrum(experiment)
            candidates[str(int(seconds))] = {
                "session": experiment.id,
                "process_time_s": seconds,
                "reflectance": measured,
                "spectral_loss": loss(measured),
            }
        winner = min(candidates, key=lambda name: candidates[name]["spectral_loss"])
        report = {
            "source": "simulation",
            "target_reflectance": TARGET,
            "winner_process_time_s": int(winner),
            "candidates": candidates,
        }
        Path(args.report).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
