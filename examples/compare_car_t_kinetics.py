"""Compare CAR receptor dwell-time designs on one seeded solid-tumor spheroid."""

import json
import time

from synthetic_lab import Lab

DESIGNS = {
    "slow_off": {
        "attachment_rate_per_min": 0.20,
        "dwell_time_min": 90.0,
    },
    "intermediate": {
        "attachment_rate_per_min": 0.20,
        "dwell_time_min": 20.0,
    },
    "fast_off": {
        "attachment_rate_per_min": 0.20,
        "dwell_time_min": 5.0,
    },
}

COMMON = {
    "car_t_cells": 160,
    "pre_growth_hours": 0.0,
    "treatment_hours": 18.0,
    "kill_rate_per_min": 0.08,
    "motility_speed_um_min": 1.0,
}


def main():
    results = {}
    with Lab("runs/physicell-car-t.sqlite") as lab:
        root = lab.create(
            "physicell-car-t-spheroid",
            seed=2029,
            config={
                "tumor_radius_um": 55.0,
                "antigen_mean": 1.0,
                "antigen_sd": 0.35,
                "antigen_negative_fraction": 0.18,
                "patient_variation": 0.0,
                "diffusion_dt_min": 0.10,
                "omp_threads": 1,
            },
        )
        untreated = root.fork()
        started = time.perf_counter()
        baseline = untreated.act(
            "infuse",
            car_t_cells=0,
            pre_growth_hours=0.0,
            treatment_hours=18.0,
            attachment_rate_per_min=0.20,
            dwell_time_min=20.0,
            kill_rate_per_min=0.08,
            motility_speed_um_min=1.0,
        )["observations"]
        baseline_viable_cells = baseline["tumor_viable_cells"]["value"]
        if baseline_viable_cells == 0:
            raise ValueError("Untreated well has no viable cells for burden normalization")
        results["no_car_t"] = {
            "tumor_viable_cells": baseline_viable_cells,
            "relative_viable_burden": 1.0,
            "tumor_viable_fraction": baseline["tumor_viable_fraction"]["value"],
            "antigen_low_viable_fraction": baseline["antigen_low_viable_fraction"]["value"],
            "wall_time_s": time.perf_counter() - started,
        }

        for name, design in DESIGNS.items():
            assay = root.fork()
            started = time.perf_counter()
            observations = assay.act("infuse", **COMMON, **design)["observations"]
            viable_cells = observations["tumor_viable_cells"]["value"]
            relative_burden = viable_cells / baseline_viable_cells
            escape = observations["antigen_low_viable_fraction"]["value"]
            exhaustion = observations["mean_exhaustion"]["value"]
            infiltration = observations["infiltrating_fraction"]["value"]
            objective = relative_burden + 0.35 * escape + 0.25 * exhaustion - 0.10 * infiltration
            results[name] = {
                "dwell_time_min": design["dwell_time_min"],
                "tumor_viable_cells": viable_cells,
                "relative_viable_burden": relative_burden,
                "tumor_viable_fraction": observations["tumor_viable_fraction"]["value"],
                "antigen_low_viable_fraction": escape,
                "antigen_low_viable_cells": observations["antigen_low_viable_cells"]["value"],
                "mean_viable_antigen": observations["mean_viable_antigen"]["value"],
                "infiltrating_fraction": infiltration,
                "infusion_radius_um": observations["infusion_radius"]["value"],
                "mean_infiltration_depth_um": observations["mean_infiltration_depth"]["value"],
                "mean_exhaustion": exhaustion,
                "exhausted_fraction": observations["exhausted_fraction"]["value"],
                "total_contacts": observations["total_contacts"]["value"],
                "total_kills": observations["total_kills"]["value"],
                "objective": objective,
                "wall_time_s": time.perf_counter() - started,
            }

    candidates = {name: value for name, value in results.items() if name != "no_car_t"}
    winner = min(candidates, key=lambda key: candidates[key]["objective"])
    print(
        json.dumps(
            {
                "question": "How does CAR receptor dwell time trade tumor control, infiltration, exhaustion and antigen escape?",
                "objective": (
                    "relative_viable_burden + 0.35*antigen_low_viable_fraction "
                    "+ 0.25*mean_exhaustion - 0.10*infiltrating_fraction"
                ),
                "selected_design": winner,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
