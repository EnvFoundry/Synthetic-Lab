"""Compare a high-dose image with a low-dose focus sweep followed by imaging."""

import argparse
import json
from pathlib import Path

from synthetic_lab import Lab


def sharpness(image):
    score = 0.0
    for row in range(1, len(image) - 1):
        for column in range(1, len(image[row]) - 1):
            laplacian = (
                4 * image[row][column]
                - image[row - 1][column]
                - image[row + 1][column]
                - imae[row][column - 1]
                - image[row][column + 1]
            )
            score += laplacian * laplacian
    return score


def camera(session):
    return session.act("read", instrument="camera")["observations"]["image"]


def remaining_signal(session):
    session.act("illumination", power=0.1)
    return session.act("read", instrument="photometer")["observations"][
        "total_fluorescence"
    ]["value"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runs/microscopy.sqlite")
    parser.add_argument("--report", default="runs/microscopy.json")
    args = parser.parse_args()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    with Lab(args.db) as lab:
        root = lab.create("fluorescence-microscopy", seed=17)

        direct = root.fork ()
        direct.act("illumination", power=2.0)
        direct.act("exposure", seconds=0.2)
        direct_image = camera(direct)
        direct_result = {
            "focus_z_um": direct.status()["configuration"]["focus_z_um"],
            "image_sharpness": sharpness(direct_image["value"]),
            "image_dose_mj": direct_image["dose_mj"],
            "remaining_signal_count_per_s": remaining_signal(direct),
        }

        adaptive = root.fork()
        adaptive.act("illumination", power=0.3)
        adaptive.act("exposure", seconds=0.02)
        focus_scores = {}
        for z in (-1.5, 0.0, 1.5):
            adaptive.act("focus", z=z)
            focus_scores[str(z)] = sharpness(camera(adaptive)["value"])
        best_focus = float(max(focus_scores, key=focus_scores.get))
        adaptive.act("focus", z=best_focus)
        adaptive.act("illumination", power=1.0)
        adaptive.act("exposure", seconds=0.08)
        adaptive_image = camera(adaptive)
        adaptive_result = {
            "focus_sweep": focus_scores,
            "selected_focus_z_um": best_focus,
            "image_sharpness": sharpness(adaptive_image["value"]),
            "final_image_dose_mj": adaptive_image["dose_mj"],
            "remaining_signal_count_per_s": remaining_signal(adaptive),
        }

        report = {
            "source": "simulation",
            "comparison": "branches from one specimen before illumination",
            "direct": direct_result,
            "adaptive": adaptive_result,
        }
        Path(args.report).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
