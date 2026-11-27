"""Choose a strong cavity resonance inside a target wavelength band."""

import json
import time

from synthetic_lab import Lab

DESIGNS = (1.25, 1.40, 1.55)
TARGET_WAVELENGTH_UM = 5.35
WAVELENGTH_TOLERANCE_UM = 0.20


def main():
    results = {}
    with Lab("runs/meep-photonics.sqlite") as lab:
        root = lab.create(
            "meep-photonic-cavity",
            seed=19,
            config={
                "resolution": 8,
                "frequency_points": 21,
                "decay_time": 35,
                "hole_radius_sigma": 0.002,
                "defect_spacing_sigma": 0.004,
                "spectrometer_noise": 0.0,
            },
        )
        for spacing in DESIGNS:
            trial = root.fork()
            trial.act("design", hole_radius=0.36, defect_spacing=spacing)
            trial.act("fabricate")
            started = time.perf_counter()
            result = trial.act("measure", instrument="summary")
            wall_time = time.perf_counter() - started
            observations = result["observations"]
            resonance = observations["resonance_wavelength"]
            wavelength = resonance["value"]
            distance = abs(wavelength - TARGET_WAVELENGTH_UM)
            results[f"{spacing:.2f}"] = {
                "resonance_wavelength_um": wavelength,
                "sampled_resonance_wavelength_um": resonance["sampled_wavelength_um"],
                "resonance_interpolated": resonance["interpolated"],
                "peak_transmission": observations["peak_transmission"]["value"],
                "spectral_contrast": observations["spectral_contrast"]["value"],
                "distance_to_target_um": distance,
                "inside_target_band": distance <= WAVELENGTH_TOLERANCE_UM,
                "wall_time_s": wall_time,
            }

    eligible = [key for key, result in results.items() if result["inside_target_band"]]
    winner = (
        max(eligible, key=lambda key: results[key]["spectral_contrast"])
        if eligible
        else min(results, key=lambda key: results[key]["distance_to_target_um"])
    )
    print(
        json.dumps(
            {
                "target_wavelength_um": TARGET_WAVELENGTH_UM,
                "wavelength_tolerance_um": WAVELENGTH_TOLERANCE_UM,
                "objective": (
                    "maximize spectral contrast inside the target band; otherwise "
                    "minimize wavelength error"
                ),
                "winner_defect_spacing_um": float(winner),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
