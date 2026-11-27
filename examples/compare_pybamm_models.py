"""Run one current protocol through PyBaMM SPM, SPMe and DFN laboratories."""

import json
import math
import time

from synthetic_lab import Lab

MODELS = (
    "pybamm-battery-spm",
    "pybamm-battery-spme",
    "pybamm-battery-dfn",
)


def main():
    results = {}
    with Lab(":memory:") as lab:
        for model in MODELS:
            started = time.perf_counter()
            cell = lab.create(
                model,
                config={
                    "initial_soc": 0.8,
                    "ambient_temperature": 298.15,
                    "sample_period": 10.0,
                },
            )
            pulse = cell.act("step", current=5.0, seconds=300.0)
            rest = cell.act("step", current=0.0, seconds=300.0)
            pulse_seconds = pulse["end_s"] - pulse["start_s"]
            rest_seconds = rest["end_s"] - rest["start_s"]
            if not all(math.isclose(duration, 300.0) for duration in (pulse_seconds, rest_seconds)):
                raise RuntimeError(f"{model} reached a cut-off; the full protocols differ")
            results[model] = {
                "wall_time_s": time.perf_counter() - started,
                "pulse_seconds": pulse_seconds,
                "rest_seconds": rest_seconds,
                "pulse_voltage_v": pulse["observations"]["terminal_voltage"]["value"],
                "rest_voltage_v": rest["observations"]["terminal_voltage"]["value"],
                "temperature_k": rest["observations"]["cell_temperature"]["value"],
                "state_of_charge": rest["observations"]["state_of_charge"]["value"],
                "termination": rest["observations"]["solver_termination"]["value"],
            }

    baseline = results["pybamm-battery-dfn"]["pulse_voltage_v"]
    for result in results.values():
        result["pulse_voltage_difference_from_dfn_v"] = result["pulse_voltage_v"] - baseline
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
