"""Compare treatment exposures on one seeded tumor-organoid response draw."""

import json
import time

from synthetic_lab import Lab

CONCENTRATIONS = (0.0, 0.6, 1.2, 2.0)
PROTOCOL = {
    "pre_culture_hours": 0.0,
    "exposure_hours": 12.0,
    "recovery_hours": 6.0,
}


def main():
    results = {}
    with Lab("runs/physicell-organoid.sqlite") as lab:
        root = lab.create(
            "physicell-tumor-organoid",
            seed=2027,
            config={
                "tumor_radius_um": 60.0,
                "resistant_fraction_mean": 0.18,
                "resistant_fraction_sd": 0.03,
                "diffusion_dt_min": 0.08,
                "omp_threads": 1,
            },
        )
        for concentration in CONCENTRATIONS:
            assay = root.fork()
            started = time.perf_counter()
            observations = assay.act(
                "expose",
                concentration=concentration,
                **PROTOCOL,
            )["observations"]
            wall_time = time.perf_counter() - started
            viable = observations["viable_cells"]["value"]
            resistant = observations["resistant_viable_fraction"]["value"]
            results[f"{concentration:.1f}"] = {
                "viable_cells": viable,
                "viable_fraction": observations["viable_fraction"]["value"],
                "apoptotic_fraction": observations["apoptotic_fraction"]["value"],
                "necrotic_fraction": observations["necrotic_fraction"]["value"],
                "resistant_viable_fraction": resistant,
                "hypoxic_viable_fraction": observations["hypoxic_viable_fraction"]["value"],
                "equivalent_diameter_um": observations["equivalent_diameter"]["value"],
                "mean_damage": observations["mean_damage"]["value"],
                "wall_time_s": wall_time,
            }

    baseline = results["0.0"]["viable_cells"]
    if baseline == 0:
        raise ValueError("Untreated well has no viable cells for burden normalization")
    for concentration, result in results.items():
        burden = result["viable_cells"] / baseline
        result["relative_viable_burden"] = burden
        result["objective"] = (
            burden + 0.35 * result["resistant_viable_fraction"] + 0.03 * float(concentration)
        )
    winner = min(results, key=lambda key: results[key]["objective"])
    print(
        json.dumps(
            {
                "protocol": PROTOCOL,
                "selected_concentration": float(winner),
                "objective": "relative_viable_burden + 0.35*resistant_viable_fraction + 0.03*concentration",
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
