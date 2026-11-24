"""Fit a heat-transfer model, test a held-out power, then change the clamp."""

import argparse
import json

from synthetic_lab import Lab
from synthetic_lab.calibration import fit_thermal


def measure(session, voltage):
    session.act("supply", voltage=voltage)
    session.act("wait", seconds=1800)
    return session.act("read")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runs/research.sqlite")
    args = parser.parse_args()
    with Lab(args.db) as lab:
        experiment = lab.create("thermal", seed=31)
        experiment.act("connect", channel="ambient")
        experiment.act("connect", channel="electrical")
        training = [measure(experiment, voltage) for voltage in (0, 2, 4)]
        fit = fit_thermal(training)
        held_out = measure(experiment, 3)["observations"]
        power = held_out["voltage"]["value"] * held_out["current"]["value"]
        predicted = (
            held_out["ambient"]["value"]
            + fit["offset_k"]
            + fit["thermal_resistance_k_per_w"] * power
        )
        baseline = experiment.fork()
        changed = experiment.fork()
        changed.act("clamp", contact="loose")
        normal = measure(baseline, 3)["observations"]["temperature"]["value"]
        loose = measure(changed, 3)["observations"]["temperature"]["value"]
        experiment.export(f"runs/{experiment.id}.jsonl")
        report = {
            "session": experiment.id,
            "source": "simulation",
            "fit": fit,
            "held_out_error_k": held_out["temperature"]["value"] - predicted,
            "same_power_normal_k": normal,
            "same_power_loose_k": loose,
            "temperature_change_k": loose - normal,
        }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
