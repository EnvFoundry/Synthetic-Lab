"""An observation-only coarse-to-fine search followed by a camera exposure."""

import json

from synthetic_lab import Lab


def main():
    with Lab("runs/fiber.sqlite") as lab:
        bench = lab.create("fiber", seed=19)
        bench.act("shutter", position="closed")
        bench.act("zero")
        bench.act("shutter", position="open")
        bench.act("laser", power={"value": 10, "unit": "mW"})
        bench.act("wait", seconds=90)
        before = bench.act("read", detector="power")["observations"]["coupled_power"]["value"]
        center_x = center_y = 0.0
        for span in (0.002, 0.0004, 0.00008):
            best = (-float("inf"), center_x, center_y)
            for ix in range(-2, 3):
                for iy in range(-2, 3):
                    x, y = center_x + ix * span / 2, center_y + iy * span / 2
                    bench.act("mirror", x=x, y=y)
                    value = bench.act("read", detector="power")["observations"]["coupled_power"][
                        "value"
                    ]
                    best = max(best, (value, x, y))
            _, center_x, center_y = best
        bench.act("mirror", x=center_x, y=center_y)
        after = bench.act("read", detector="power")["observations"]["coupled_power"]["value"]
        bench.act("exposure", seconds=0.001)
        image = bench.act("read", detector="camera")["observations"]["image"]
        bench.export(f"runs/{bench.id}.jsonl")
        print(
            json.dumps(
                {
                    "session": bench.id,
                    "source": "simulation",
                    "before_w": before,
                    "after_w": after,
                    "saturated_pixels": image["saturated_pixels"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
