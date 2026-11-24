"""Paraxial Gaussian fiber coupling, warming laser and finite-range detectors."""

import math

from ..model import Model, Parameter, reading


class FiberBench(Model):
    name = "fiber"
    description = (
        "Align a drifting Gaussian coupling peak with a power meter, reference diode and camera."
    )
    defaults = {"width": 0.0008, "warmup": 15.0, "drift": 0.0000002, "sensor_noise": 0.00001}
    parameters = {
        "width": Parameter("rad", 0.0002, 0.002),
        "warmup": Parameter("s", 0.1, 300),
        "drift": Parameter(None, 0, 0.000001),
        "sensor_noise": Parameter("W", 0, 0.0001),
    }
    actions = {
        "laser": {"power": Parameter("W", 0, 0.05)},
        "mirror": {"x": Parameter("rad", -0.005, 0.005), "y": Parameter("rad", -0.005, 0.005)},
        "shutter": {"position": Parameter(choices=("open", "closed"))},
        "exposure": {"seconds": Parameter("s", 0.00001, 0.1)},
        "read": {"detector": Parameter(choices=("power", "reference", "camera"))},
        "zero": {},
        "wait": {"seconds": Parameter("s", 0, 3600)},
    }

    def initial(self, rng):
        return {
            "time_s": 0.0,
            "set_power": 0.0,
            "power": 0.0,
            "x": 0.0,
            "y": 0.0,
            "center_x": rng.uniform(-0.0015, 0.0015),
            "center_y": rng.uniform(-0.0015, 0.0015),
            "phase": rng.uniform(0, 2 * math.pi),
            "exposure": 0.01,
            "shutter": "open",
            "zero": 0.0,
            "dark_offset": rng.uniform(0.00001, 0.00005),
        }

    def advance(self, state, seconds):
        state["power"] = state["set_power"] + (state["power"] - state["set_power"]) * math.exp(
            -seconds / self.config["warmup"]
        )
        state["time_s"] += seconds

    def signal(self, state):
        t = state["time_s"]
        x = state["center_x"] + self.config["drift"] * t
        y = state["center_y"] - self.config["drift"] * 0.5 * t
        power = state["power"] * (1 + 0.015 * math.sin(t / 23 + state["phase"]))
        if state["shutter"] == "closed":
            power = 0.0
        distance = (state["x"] - x) ** 2 + (state["y"] - y) ** 2
        coupled = power * 0.85 * math.exp(-distance / (2 * self.config["width"] ** 2))
        return power, coupled

    def perform(self, state, rng, action, params):
        if action == "wait":
            self.advance(state, params["seconds"])
        elif action == "laser":
            state["set_power"] = params["power"]
            self.advance(state, 0.01)
        elif action == "mirror":
            state.update(x=params["x"], y=params["y"])
            self.advance(state, 0.1)
        elif action == "shutter":
            state["shutter"] = params["position"]
            self.advance(state, 0.02)
        elif action == "exposure":
            state["exposure"] = params["seconds"]
        elif action == "zero":
            if state["shutter"] != "closed":
                raise ValueError("Close the shutter before zeroing the power meter")
            self.advance(state, 0.05)
            state["zero"] = state["dark_offset"] + rng.gauss(0, self.config["sensor_noise"])
        elif action == "read":
            detector = params["detector"]
            duration = state["exposure"] if detector == "camera" else 0.05
            # Midpoint integration resolves the short detector window without resetting drift.
            source, coupled = 0.0, 0.0
            for _ in range(8):
                self.advance(state, duration / 16)
                p, c = self.signal(state)
                source += p / 8
                coupled += c / 8
                self.advance(state, duration / 16)
            if detector == "reference":
                noise = self.config["sensor_noise"]
                return {
                    "reference_power": reading(
                        source + rng.gauss(0, noise), "W", noise, window_s=duration
                    )
                }
            if detector == "power":
                noise = self.config["sensor_noise"]
                raw = coupled + state["dark_offset"] - state["zero"] + rng.gauss(0, noise)
                return {
                    "coupled_power": reading(
                        min(raw, 0.02), "W", noise, saturated=raw >= 0.02, window_s=duration
                    )
                }
            pixels = []
            clipped = 0
            for row in range(16):
                line = []
                for column in range(16):
                    # Counts describe a fixed image of the fiber output face.
                    expected = 12 + 8e7 * coupled * duration * math.exp(
                        -((row - 7.5) ** 2 + (column - 7.5) ** 2) / 8
                    )
                    count = round(rng.gauss(expected, math.sqrt(expected + 4)))
                    clipped += count >= 4095
                    line.append(max(0, min(4095, count)))
                pixels.append(line)
            return {
                "image": {
                    "value": pixels,
                    "unit": "count",
                    "shape": [16, 16],
                    "axes": ["row", "column"],
                    "window_s": duration,
                    "saturated_pixels": clipped,
                    "noise_model": "Gaussian approximation to shot noise plus read noise",
                }
            }
        return {}

    def visible(self, state):
        return {
            "set_power_w": state["set_power"],
            "mirror_x_rad": state["x"],
            "mirror_y_rad": state["y"],
            "exposure_s": state["exposure"],
            "shutter": state["shutter"],
            "power_zero_w": state["zero"],
        }
