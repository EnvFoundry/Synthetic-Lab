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
                "omp_threads": 2,
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
            viable = observations["viable_fraction"]["value"]
            resistant = observations["resistant_viable_fraction"]["value"]
            # Prefer tumor suppression while penalizing selection for a resistant remnant
            # and unnecessary external exposure.
            objective = viable + 0.35 * resistant + 0.03 * concentration
            results[f"{concentration:.1f}"] = {
                "viable_fraction": viable,
                "apoptotic_fraction": observations["apoptotic_fraction"]["value"],
                "necrotic_fraction": observations["necrotic_fraction"]["value"],
                "resistant_viable_fraction": resistant,
                "hypoxic_viable_fraction": observations["hypoxic_viable_fraction"]["value"],
                "equivalent_diameter_um": observations["equivalent_diameter"]["value"],
                "mean_damage": observations["mean_damage"]["value"],
                "objective": objective,
                "wall_time_s": wall_time,
            }

    winner = min(results, key=lambda key: results[key]["objective"])
    print(
        json.dumps(
            {
                "protocol": PROTOCOL,
                "selected_concentration": float(winner),
                "objective": "viable_fraction + 0.35*resistant_viable_fraction + 0.03*concentration",
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
