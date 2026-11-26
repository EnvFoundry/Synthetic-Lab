"""Consecutive catalytic reaction with Arrhenius kinetics and a thermal jacket."""

import math

from ..model import Model, Parameter, reading

R_GAS = 8.314462618


class ReactionBench(Model):
    name = "reaction"
    description = (
        "Choose a temperature programme and measurements for a catalytic "
        "A-to-B-to-C batch reaction."
    )
    defaults = {
        "initial_substrate": 1.0,
        "volume": 0.25,
        "ambient": 298.15,
        "initial_temperature": 298.15,
        "preexponential_1": 3.0e5,
        "activation_energy_1": 50000.0,
        "preexponential_2": 2.0e6,
        "activation_energy_2": 60000.0,
        "deactivation_preexponential": 1.0e6,
        "deactivation_energy": 70000.0,
        "enthalpy_1": 50000.0,
        "enthalpy_2": 20000.0,
        "heat_capacity": 500.0,
        "heat_transfer": 4.0,
        "jacket_power": 300.0,
        "controller_gain": 12.0,
        "shutdown_temperature": 475.0,
        "variation": 0.15,
    }
    parameters = {
        "initial_substrate": Parameter("mol/L", 0.05, 2.0),
        "volume": Parameter("L", 0.01, 5.0),
        "ambient": Parameter("K", 280.0, 330.0),
        "initial_temperature": Parameter("K", 280.0, 400.0),
        "preexponential_1": Parameter("1/s", 1.0e2, 1.0e9),
        "activation_energy_1": Parameter("J/mol", 10000.0, 120000.0),
        "preexponential_2": Parameter("1/s", 1.0e2, 1.0e9),
        "activation_energy_2": Parameter("J/mol", 10000.0, 120000.0),
        "deactivation_preexponential": Parameter("1/s", 0.0, 1.0e10),
        "deactivation_energy": Parameter("J/mol", 10000.0, 160000.0),
        "enthalpy_1": Parameter("J/mol", 0.0, 200000.0),
        "enthalpy_2": Parameter("J/mol", 0.0, 200000.0),
        "heat_capacity": Parameter("J/K", 10.0, 5000.0),
        "heat_transfer": Parameter("W/K", 0.1, 100.0),
        "jacket_power": Parameter("W", 1.0, 5000.0),
        "controller_gain": Parameter("W/K", 0.1, 1000.0),
        "shutdown_temperature": Parameter("K", 330.0, 600.0),
        "variation": Parameter(None, 0.0, 0.5),
    }
    actions = {
        "set_temperature": {"setpoint": Parameter("K", 290.0, 450.0)},
        "read": {
            "instrument": Parameter(
                choices=("thermometer", "spectrometer", "chromatograph")
            )
        },
        "wait": {"seconds": Parameter("s", 0.0, 7200.0)},
    }

    def initial(self, rng):
        variation = self.config["variation"]

        def scale():
            return rng.uniform(1.0 - variation, 1.0 + variation)

        return {
            "time_s": 0.0,
            "temperature": self.config["initial_temperature"],
            "setpoint": self.config["initial_temperature"],
            "a": self.config["initial_substrate"],
            "b": 0.0,
            "c": 0.0,
            "activity": 1.0,
            "rate_scale_1": scale(),
            "rate_scale_2": scale(),
            "deactivation_scale": scale(),
            "spectral_baseline": rng.uniform(-0.01, 0.01),
            "protection": "ready",
            "reads": 0,
        }

    def rate_constants(self, state):
        temperature = state["temperature"]
        activity = state["activity"]
        k1 = (
            self.config["preexponential_1"]
            * state["rate_scale_1"]
            * math.exp(-self.config["activation_energy_1"] / (R_GAS * temperature))
            * activity
        )
        k2 = (
            self.config["preexponential_2"]
            * state["rate_scale_2"]
            * math.exp(-self.config["activation_energy_2"] / (R_GAS * temperature))
            * activity
        )
        kd = (
            self.config["deactivation_preexponential"]
            * state["deactivation_scale"]
            * math.exp(-self.config["deactivation_energy"] / (R_GAS * temperature))
        )
        return k1, k2, kd

    @staticmethod
    def _consecutive(a0, b0, c0, k1, k2, seconds):
        decay1 = math.exp(-k1 * seconds)
        decay2 = math.exp(-k2 * seconds)
        a1 = a0 * decay1
        if abs(k2 - k1) <= 1e-12 * max(1.0, k1, k2):
            b1 = (b0 + a0 * k1 * seconds) * decay1
        else:
            b1 = b0 * decay2 + a0 * k1 * (decay1 - decay2) / (k2 - k1)
        total = a0 + b0 + c0
        a1 = max(0.0, min(total, a1))
        b1 = max(0.0, min(total - a1, b1))
        c1 = total - a1 - b1
        return a1, b1, c1

    def _step(self, state, seconds):
        a0, b0, c0 = state["a"], state["b"], state["c"]
        k1, k2, kd = self.rate_constants(state)
        a1, b1, c1 = self._consecutive(a0, b0, c0, k1, k2, seconds)
        extent1 = a0 - a1
        extent2 = c1 - c0
        state.update(a=a1, b=b1, c=c1)
        state["activity"] *= math.exp(-kd * seconds)

        reaction_heat = self.config["volume"] * (
            self.config["enthalpy_1"] * extent1 + self.config["enthalpy_2"] * extent2
        )
        reaction_power = reaction_heat / seconds if seconds else 0.0
        requested = self.config["controller_gain"] * (
            state["setpoint"] - state["temperature"]
        )
        jacket_power = max(
            -self.config["jacket_power"], min(self.config["jacket_power"], requested)
        )
        conductance = self.config["heat_transfer"]
        equilibrium = self.config["ambient"] + (jacket_power + reaction_power) / conductance
        decay = math.exp(-conductance * seconds / self.config["heat_capacity"])
        state["temperature"] = equilibrium + (state["temperature"] - equilibrium) * decay
        if state["temperature"] >= self.config["shutdown_temperature"]:
            state["protection"] = "tripped"
            state["setpoint"] = self.config["ambient"]
        state["time_s"] += seconds

    def advance(self, state, seconds):
        remaining = seconds
        while remaining > 1e-12:
            step = min(0.5, remaining)
            self._step(state, step)
            remaining -= step

    def perform(self, state, rng, action, params):
        if action == "set_temperature":
            if state["protection"] == "tripped" and params["setpoint"] > self.config["ambient"]:
                raise ValueError(
                    "Thermal protection is latched; only cooling setpoints are accepted"
                )
            state["setpoint"] = params["setpoint"]
            self.advance(state, 0.1)
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            instrument = params["instrument"]
            duration = {"thermometer": 0.2, "spectrometer": 1.0, "chromatograph": 20.0}[
                instrument
            ]
            self.advance(state, duration)
            state["reads"] += 1
            if instrument == "thermometer":
                noise = 0.08
                return {
                    "temperature": reading(
                        state["temperature"] + rng.gauss(0.0, noise),
                        "K",
                        noise,
                        window_s=duration,
                    )
                }
            if instrument == "chromatograph":
                noise = 0.004
                return {
                    species: reading(
                        max(0.0, state[species] + rng.gauss(0.0, noise)),
                        "mol/L",
                        noise,
                        detection_limit=0.001,
                        window_s=duration,
                    )
                    for species in ("a", "b", "c")
                }
            coefficients = (
                (1.25, 0.18, 0.05),
                (0.12, 1.50, 0.24),
                (0.04, 0.30, 1.10),
            )
            wavelengths = (450, 520, 610)
            noise = 0.003
            thermal_baseline = 0.00015 * (
                state["temperature"] - self.config["ambient"]
            )
            values = [
                state["spectral_baseline"]
                + thermal_baseline
                + row[0] * state["a"]
                + row[1] * state["b"]
                + row[2] * state["c"]
                + rng.gauss(0.0, noise)
                for row in coefficients
            ]
            return {
                "absorbance": {
                    "value": values,
                    "unit": "absorbance",
                    "noise_std": noise,
                    "shape": [3],
                    "axes": ["wavelength_nm"],
                    "axis_values": list(wavelengths),
                    "window_s": duration,
                }
            }
        return {}

    def visible(self, state):
        return {
            "temperature_setpoint_k": state["setpoint"],
            "thermal_protection": state["protection"],
            "measurement_count": state["reads"],
        }
