"""A resistive heater, exchangeable clamp and attachable electrical metering."""

import math

from ..model import Model, Parameter, reading


class ThermalBench(Model):
    name = "thermal"
    description = "Distinguish heating power from thermal contact using temperature and electrical measurements."
    defaults = {
        "thermal_resistance": 10.0,
        "heat_capacity": 12.0,
        "resistance": 20.0,
        "ambient": 295.15,
        "variation": 0.2,
        "sensor_noise": 0.03,
    }
    parameters = {
        "thermal_resistance": Parameter("K/W", 1, 50),
        "heat_capacity": Parameter("J/K", 1, 100),
        "resistance": Parameter("ohm", 5, 100),
        "ambient": Parameter("K", 280, 310),
        "variation": Parameter(None, 0, 0.4),
        "sensor_noise": Parameter(None, 0, 1),
    }
    actions = {
        "supply": {"voltage": Parameter("V", 0, 5)},
        "clamp": {"contact": Parameter(choices=("normal", "loose"))},
        "connect": {"channel": Parameter(choices=("electrical", "ambient"))},
        "read": {},
        "wait": {"seconds": Parameter("s", 0, 3600)},
    }

    def initial(self, rng):
        variation = self.config["variation"]
        return {
            "time_s": 0.0,
            "voltage": 0.0,
            "contact": "normal",
            "channels": ["temperature"],
            "temperature": self.config["ambient"],
            "energy_j": 0.0,
            "lost_heat_j": 0.0,
            "thermal_resistance": self.config["thermal_resistance"]
            * rng.uniform(1 - variation, 1 + variation),
            "heater_resistance": self.config["resistance"]
            * rng.uniform(1 - variation, 1 + variation),
            "supply_gain": rng.uniform(1 - variation / 5, 1 + variation / 5),
            "temperature_offset": rng.uniform(-0.15, 0.15),
        }

    def advance(self, state, seconds):
        actual_voltage = state["voltage"] * state["supply_gain"]
        power = actual_voltage**2 / state["heater_resistance"]
        resistance = state["thermal_resistance"] * (1.6 if state["contact"] == "loose" else 1)
        capacity = self.config["heat_capacity"]
        equilibrium = self.config["ambient"] + power * resistance
        before = state["temperature"]
        state["temperature"] = equilibrium + (before - equilibrium) * math.exp(
            -seconds / (resistance * capacity)
        )
        state["energy_j"] += power * seconds
        state["lost_heat_j"] += power * seconds - capacity * (state["temperature"] - before)
        state["time_s"] += seconds

    def perform(self, state, rng, action, params):
        if action == "wait":
            self.advance(state, params["seconds"])
        elif action == "supply":
            state["voltage"] = params["voltage"]
            self.advance(state, 0.02)
        elif action == "clamp":
            state["contact"] = params["contact"]
            self.advance(state, 2.0)
        elif action == "connect":
            channel = params["channel"]
            if channel not in state["channels"]:
                state["channels"].append(channel)
                self.advance(state, 1.0)
        elif action == "read":
            self.advance(state, 0.2)
            noise = self.config["sensor_noise"]
            result = {
                "temperature": reading(
                    state["temperature"] + state["temperature_offset"] + rng.gauss(0, noise),
                    "K",
                    noise,
                )
            }
            if "ambient" in state["channels"]:
                result["ambient"] = reading(
                    self.config["ambient"] + rng.gauss(0, noise), "K", noise
                )
            if "electrical" in state["channels"]:
                voltage = state["voltage"] * state["supply_gain"]
                result["voltage"] = reading(voltage + rng.gauss(0, 0.001), "V", 0.001)
                result["current"] = reading(
                    voltage / state["heater_resistance"] + rng.gauss(0, 0.0001), "A", 0.0001
                )
            return result
        return {}

    def visible(self, state):
        return {
            "supply_v": state["voltage"],
            "contact": state["contact"],
            "connected_channels": list(state["channels"]),
        }
