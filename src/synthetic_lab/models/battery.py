"""One-RC equivalent circuit with charge balance, self-heating and protection."""

import math

from ..model import Model, Parameter, reading


class Battery(Model):
    name = "battery"
    description = (
        "Choose current pulses and rest periods to study cell resistance, relaxation and heating."
    )
    defaults = {
        "capacity": 2.5,
        "ohmic_resistance": 0.06,
        "polarization_resistance": 0.03,
        "relaxation": 45.0,
        "thermal_resistance": 8.0,
        "heat_capacity": 120.0,
        "ambient": 295.15,
        "variation": 0.15,
    }
    parameters = {
        "capacity": Parameter("Ah", 0.5, 10),
        "ohmic_resistance": Parameter("ohm", 0.01, 0.3),
        "polarization_resistance": Parameter("ohm", 0.005, 0.2),
        "relaxation": Parameter("s", 5, 300),
        "thermal_resistance": Parameter("K/W", 1, 20),
        "heat_capacity": Parameter("J/K", 20, 500),
        "ambient": Parameter("K", 280, 310),
        "variation": Parameter(None, 0, 0.3),
    }
    actions = {
        "load": {"current": Parameter("A", -2, 2)},
        "wait": {"seconds": Parameter("s", 0, 3600)},
        "read": {},
    }

    def initial(self, rng):
        v = self.config["variation"]
        capacity = self.config["capacity"] * 3600 * rng.uniform(1 - v, 1 + v)
        return {
            "time_s": 0.0,
            "current": 0.0,
            "charge_c": capacity * rng.uniform(0.45, 0.75),
            "capacity_c": capacity,
            "polarization_v": 0.0,
            "r0": self.config["ohmic_resistance"] * rng.uniform(1 - v, 1 + v),
            "temperature": self.config["ambient"],
            "throughput_c": 0.0,
            "protection": "ready",
        }

    def voltage(self, state):
        soc = state["charge_c"] / state["capacity_c"]
        ocv = 3.0 + 1.2 * soc + 0.04 * math.tanh((soc - 0.5) * 8)
        return ocv - state["current"] * state["r0"] - state["polarization_v"]

    def advance(self, state, seconds):
        remaining = seconds
        while remaining > 1e-10:
            dt = min(1.0, remaining)
            current = state["current"]
            if current > 0:
                dt = min(dt, state["charge_c"] / current)
            elif current < 0:
                dt = min(dt, (state["capacity_c"] - state["charge_c"]) / (-current))
            if dt < 1e-10:
                state["current"] = 0.0
                state["protection"] = "tripped"
                continue
            state["charge_c"] = max(0.0, min(state["capacity_c"], state["charge_c"] - current * dt))
            state["throughput_c"] += abs(current) * dt
            r1 = self.config["polarization_resistance"]
            p_before = state["polarization_v"]
            state["polarization_v"] = current * r1 + (p_before - current * r1) * math.exp(
                -dt / self.config["relaxation"]
            )
            midpoint_p = 0.5 * (p_before + state["polarization_v"])
            heat = current**2 * state["r0"] + midpoint_p**2 / r1
            equilibrium = self.config["ambient"] + heat * self.config["thermal_resistance"]
            tau = self.config["thermal_resistance"] * self.config["heat_capacity"]
            state["temperature"] = equilibrium + (state["temperature"] - equilibrium) * math.exp(
                -dt / tau
            )
            state["time_s"] += dt
            remaining -= dt
            voltage = self.voltage(state)
            if (
                voltage < 2.7
                or voltage > 4.25
                or state["temperature"] > 323.15
                or state["charge_c"] in (0, state["capacity_c"])
            ):
                state["current"] = 0.0
                state["protection"] = "tripped"

    def perform(self, state, rng, action, params):
        if action == "load":
            if state["protection"] == "tripped" and params["current"] != 0:
                raise ValueError(
                    "Cell protection is latched; observe this cell or start a new specimen"
                )
            state["current"] = params["current"]
            self.advance(state, 0.02)
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            self.advance(state, 0.05)
            return {
                "voltage": reading(self.voltage(state) + rng.gauss(0, 0.001), "V", 0.001),
                "current": reading(state["current"] + rng.gauss(0, 0.0005), "A", 0.0005),
                "temperature": reading(state["temperature"] + rng.gauss(0, 0.03), "K", 0.03),
            }
        return {}

    def visible(self, state):
        return {
            "load_a": state["current"],
            "protection": state["protection"],
            "current_convention": "positive discharges the cell",
        }
