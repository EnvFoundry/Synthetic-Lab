"""Fed-batch bioreactor observed by OD, fluorescence, Raman and an oxygen optode."""

import math

from synthetic_lab.model import Model, Parameter, reading

from .contract import RESEARCH
from .physics import advance, concentrations

RAMAN_SHIFTS_CM = (820.0, 1005.0, 1125.0, 1450.0, 1660.0)


class SpectroscopicBioreactor(Model):
    name = "spectroscopic-bioreactor"
    version = "2"
    description = (
        "Schedule feed, aeration, temperature and optical induction while estimating a "
        "fed-batch culture from complementary optical measurements."
    )
    defaults = {
        "initial_volume": 1.0,
        "maximum_volume": 2.0,
        "initial_biomass": 0.35,
        "initial_substrate": 18.0,
        "feed_substrate": 180.0,
        "mu_max": 0.48,
        "ks": 0.8,
        "ko": 8.0,
        "yield_xs": 0.52,
        "yield_ps": 0.65,
        "qp_max": 0.22,
        "kla": 28.0,
        "oxygen_uptake": 95.0,
        "reporter_tau": 0.35,
        "burden_tau": 0.7,
        "temperature_optimum": 310.15,
        "temperature_width": 8.0,
        "thermal_tau": 600.0,
        "variation": 0.12,
    }
    parameters = {
        "initial_volume": Parameter("L", 0.1, 20.0),
        "maximum_volume": Parameter("L", 0.2, 50.0),
        "initial_biomass": Parameter("g/L", 0.01, 20.0),
        "initial_substrate": Parameter("g/L", 0.0, 500.0),
        "feed_substrate": Parameter("g/L", 0.0, 1000.0),
        "mu_max": Parameter("1/h", 0.01, 2.0),
        "ks": Parameter("g/L", 0.001, 100.0),
        "ko": Parameter("%", 0.1, 100.0),
        "yield_xs": Parameter("g/g", 0.05, 1.5),
        "yield_ps": Parameter("g/g", 0.05, 2.0),
        "qp_max": Parameter("g/g/h", 0.0, 2.0),
        "kla": Parameter("1/h", 0.1, 300.0),
        "oxygen_uptake": Parameter("% L/g", 0.0, 500.0),
        "reporter_tau": Parameter("h", 0.01, 20.0),
        "burden_tau": Parameter("h", 0.01, 20.0),
        "temperature_optimum": Parameter("K", 280.0, 330.0),
        "temperature_width": Parameter("K", 1.0, 50.0),
        "thermal_tau": Parameter("s", 10.0, 7200.0),
        "variation": Parameter(None, 0.0, 0.5),
    }
    actions = {
        "feed": {"rate": Parameter("L/h", 0.0, 0.25)},
        "aeration": {"kla": Parameter("1/h", 0.0, 120.0)},
        "temperature": {"setpoint": Parameter("K", 290.0, 325.0)},
        "induction": {"level": Parameter(None, 0.0, 1.0)},
        "read": {"instrument": Parameter(choices=("od600", "fluorescence", "raman", "optode"))},
        "wait": {"seconds": Parameter("s", 0.0, 86400.0)},
    }
    research = RESEARCH

    def initial(self, rng):
        if self.config["maximum_volume"] < self.config["initial_volume"]:
            raise ValueError("maximum_volume must be at least initial_volume")
        variation = self.config["variation"]
        volume = self.config["initial_volume"]
        return {
            "time_s": 0.0,
            "volume_l": volume,
            "biomass_g": self.config["initial_biomass"] * volume,
            "substrate_g": self.config["initial_substrate"] * volume,
            "product_g": 0.0,
            "feed_rate_l_h": 0.0,
            "kla_h": self.config["kla"],
            "temperature_k": self.config["temperature_optimum"],
            "temperature_setpoint_k": self.config["temperature_optimum"],
            "induction": 0.0,
            "reporter": 0.0,
            "burden": 0.0,
            "oxygen_percent": rng.uniform(75.0, 90.0),
            "growth_scale": rng.uniform(1.0 - variation, 1.0 + variation),
            "product_scale": rng.uniform(1.0 - variation, 1.0 + variation),
            "spectral_gain": rng.uniform(0.96, 1.04),
            "fluorescence_gain": rng.uniform(0.9, 1.1),
            "substrate_fed_g": 0.0,
            "substrate_consumed_g": 0.0,
        }

    concentrations = staticmethod(concentrations)

    def advance(self, state, seconds):
        advance(self.config, state, seconds)

    def _raman(self, state):
        biomass, substrate, product = self.concentrations(state)
        response = (
            (0.055, 0.008, 0.020),
            (0.020, 0.030, 0.160),
            (0.085, 0.018, 0.035),
            (0.015, 0.180, 0.050),
            (0.030, 0.100, 0.090),
        )
        return [
            state["spectral_gain"] * (row[0] * substrate + row[1] * product + row[2] * biomass)
            for row in response
        ]

    def perform(self, state, rng, action, params):
        if action == "feed":
            state["feed_rate_l_h"] = params["rate"]
            self.advance(state, 0.1)
        elif action == "aeration":
            state["kla_h"] = params["kla"]
            self.advance(state, 0.1)
        elif action == "temperature":
            state["temperature_setpoint_k"] = params["setpoint"]
            self.advance(state, 0.1)
        elif action == "induction":
            state["induction"] = params["level"]
            self.advance(state, 0.05)
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            instrument = params["instrument"]
            duration = {
                "od600": 0.5,
                "fluorescence": 1.0,
                "raman": 5.0,
                "optode": 0.2,
            }[instrument]
            self.advance(state, duration)
            biomass, _, _ = self.concentrations(state)
            if instrument == "od600":
                ideal = 1.15 * biomass / (1.0 + biomass / 4.5)
                noise = 0.008
                return {
                    "od600": reading(
                        max(0.0, ideal + rng.gauss(0.0, noise)),
                        None,
                        noise,
                        window_s=duration,
                    )
                }
            if instrument == "fluorescence":
                ideal = 24000.0 * biomass * state["reporter"] * state["fluorescence_gain"]
                noise = max(20.0, math.sqrt(max(ideal, 1.0)))
                return {
                    "reporter_fluorescence": reading(
                        max(0.0, ideal + rng.gauss(0.0, noise)),
                        "count/s",
                        noise,
                        window_s=duration,
                    )
                }
            if instrument == "optode":
                noise = 0.4
                return {
                    "dissolved_oxygen": reading(
                        max(
                            0.0,
                            min(
                                100.0,
                                state["oxygen_percent"] + rng.gauss(0.0, noise),
                            ),
                        ),
                        "%",
                        noise,
                        window_s=duration,
                    )
                }

            noise = 0.01
            values = [max(0.0, value + rng.gauss(0.0, noise)) for value in self._raman(state)]
            return {
                "raman_intensity": {
                    "value": values,
                    "unit": "a.u.",
                    "noise_std": noise,
                    "shape": [len(values)],
                    "axes": ["raman_shift_cm-1"],
                    "axis_values": list(RAMAN_SHIFTS_CM),
                    "window_s": duration,
                }
            }
        return {}

    def visible(self, state):
        return {
            "feed_rate_l_h": state["feed_rate_l_h"],
            "kla_h": state["kla_h"],
            "temperature_setpoint_k": state["temperature_setpoint_k"],
            "induction_level": state["induction"],
        }
