"""Thin-film growth observed by spectroscopic reflectometry and interferometry."""

import cmath
import math

from synthetic_lab.model import Model, Parameter, reading
from synthetic_lab.research import ResearchContract

R_GAS = 8.314462618
WAVELENGTHS_NM = (450.0, 500.0, 550.0, 600.0, 650.0, 700.0, 750.0, 800.0)


class ThinFilmBench(Model):
    name = "thin-film"
    description = (
        "Deposit and anneal an optical film while observing thickness-dependent interference, "
        "roughness and densification."
    )
    defaults = {
        "substrate_index": 1.52,
        "bulk_index": 2.12,
        "extinction": 0.004,
        "rate_gain": 1.0,
        "deposition_porosity": 0.14,
        "residual_porosity": 0.025,
        "base_roughness": 0.35,
        "roughness_per_nm": 0.0018,
        "thermal_time": 45.0,
        "anneal_preexponential": 20.0,
        "anneal_activation": 55000.0,
        "ambient": 298.15,
        "variation": 0.08,
    }
    parameters = {
        "substrate_index": Parameter(None, 1.2, 4.5),
        "bulk_index": Parameter(None, 1.2, 5.0),
        "extinction": Parameter(None, 0.0, 0.5),
        "rate_gain": Parameter(None, 0.5, 1.5),
        "deposition_porosity": Parameter(None, 0.0, 0.5),
        "residual_porosity": Parameter(None, 0.0, 0.3),
        "base_roughness": Parameter("nm", 0.0, 20.0),
        "roughness_per_nm": Parameter(None, 0.0, 0.05),
        "thermal_time": Parameter("s", 1.0, 1000.0),
        "anneal_preexponential": Parameter("1/s", 0.0, 1.0e5),
        "anneal_activation": Parameter("J/mol", 1000.0, 200000.0),
        "ambient": Parameter("K", 270.0, 330.0),
        "variation": Parameter(None, 0.0, 0.3),
    }
    actions = {
        "deposition": {"rate": Parameter("nm/s", 0.0, 2.0)},
        "shutter": {"position": Parameter(choices=("open", "closed"))},
        "temperature": {"setpoint": Parameter("K", 280.0, 800.0)},
        "read": {
            "instrument": Parameter(
                choices=("reflectometer", "interferometer", "pyrometer")
            )
        },
        "wait": {"seconds": Parameter("s", 0.0, 7200.0)},
    }
    research = ResearchContract(
        domains=(
            "thin-film materials",
            "semiconductor fabrication",
            "photonics",
            "optical metrology",
        ),
        phenomena=(
            "thin-film interference",
            "deposition-rate variation",
            "porosity-driven refractive-index change",
            "surface roughness",
            "thermal densification",
        ),
        questions=(
            "Which deposition endpoint produces a target reflectance spectrum?",
            "Can multi-wavelength reflectometry separate thickness from refractive index?",
            "How does annealing trade densification against process time?",
            "Which optical measurement resolves a periodic thickness ambiguity?",
        ),
        observables={
            "reflectance": {
                "unit": None,
                "description": "Eight-channel normal-incidence reflectance spectrum.",
            },
            "phase": {
                "unit": "rad",
                "description": "Single-wavelength interferometric phase modulo two pi.",
            },
            "visibility": {
                "unit": None,
                "description": "Interference visibility reduced by surface roughness.",
            },
            "temperature": {
                "unit": "K",
                "description": "Optical pyrometer estimate of specimen temperature.",
            },
        },
        latent_variables={
            "thickness": {
                "unit": "nm",
                "description": "Physical film thickness accumulated during open-shutter growth.",
            },
            "effective_index": {
                "unit": None,
                "description": "Refractive index set by material and evolving porosity.",
            },
            "roughness": {
                "unit": "nm",
                "description": "RMS surface roughness affecting optical visibility.",
            },
            "rate_gain": {
                "unit": None,
                "description": (
                    "Specimen-specific difference between commanded and actual growth rate."
                ),
            },
        },
        interventions=("deposition", "shutter", "temperature"),
        invariants=(
            (
                "Film thickness changes only while the shutter is open and deposition "
                "rate is positive."
            ),
            "Reflectance remains between zero and one.",
            "Porosity remains between its residual and as-deposited bounds.",
        ),
        validity_conditions=(
            "One homogeneous isotropic film on a semi-infinite substrate.",
            "Normal-incidence coherent reflection with a scalar complex refractive index.",
            "Uniform thickness, temperature, porosity and roughness across the measured area.",
        ),
        limitations=(
            "No multilayers, anisotropy, lateral nonuniformity or wavelength-dependent dispersion.",
            "Roughness enters through a scalar attenuation approximation.",
            "Process coefficients are generic rather than tied to a named deposition tool.",
        ),
        failure_conditions=(
            (
                "A single-wavelength phase repeats every optical half wavelength and is "
                "ambiguous alone."
            ),
            "Very rough or absorbing films suppress useful interference contrast.",
            "The one-layer model ceases to represent a graded or multilayer coating.",
        ),
        fidelity="reduced-order",
        action_semantics={
            "deposition": {
                "kind": "control",
                "description": "Set the nominal film growth rate.",
            },
            "shutter": {
                "kind": "intervention",
                "description": "Start or stop material arriving at the specimen.",
            },
            "temperature": {
                "kind": "control",
                "description": "Set the substrate-heater target.",
            },
            "read": {
                "kind": "measurement",
                "description": "Acquire one optical metrology channel.",
            },
            "wait": {
                "kind": "wait",
                "description": "Advance growth, heating and densification without observing.",
            },
        },
        reference_methods=(
            "transfer-matrix spectral fitting",
            "multi-wavelength endpoint control",
            "phase unwrapping with spectral reflectance",
            "held-out anneal prediction",
        ),
        physical_counterpart=(
            "A deposition chamber with broadband reflectometry, phase interferometry and pyrometry"
        ),
    )

    def initial(self, rng):
        variation = self.config["variation"]
        return {
            "time_s": 0.0,
            "thickness_nm": 0.0,
            "porosity": self.config["deposition_porosity"],
            "roughness_nm": self.config["base_roughness"],
            "temperature_k": self.config["ambient"],
            "temperature_setpoint_k": self.config["ambient"],
            "rate_command_nm_s": 0.0,
            "rate_gain": self.config["rate_gain"]
            * rng.uniform(1.0 - variation, 1.0 + variation),
            "bulk_index": self.config["bulk_index"]
            * rng.uniform(1.0 - variation / 2.0, 1.0 + variation / 2.0),
            "shutter": "closed",
            "spectral_gain": rng.uniform(0.995, 1.005),
            "spectral_offset": rng.uniform(-0.0015, 0.0015),
        }

    def effective_index(self, state):
        return state["bulk_index"] * (1.0 - 0.35 * state["porosity"])

    def reflectance(self, state, wavelength_nm):
        n0 = 1.0 + 0j
        n1 = complex(self.effective_index(state), -self.config["extinction"])
        n2 = complex(self.config["substrate_index"], 0.0)
        r01 = (n0 - n1) / (n0 + n1)
        r12 = (n1 - n2) / (n1 + n2)
        phase = 2.0 * math.pi * n1 * state["thickness_nm"] / wavelength_nm
        propagation = cmath.exp(2j * phase)
        amplitude = (r01 + r12 * propagation) / (1.0 + r01 * r12 * propagation)
        roughness = (
            1.0
            if state["thickness_nm"] == 0.0
            else math.exp(
                -((4.0 * math.pi * state["roughness_nm"] / wavelength_nm) ** 2)
            )
        )
        return max(0.0, min(1.0, abs(amplitude) ** 2 * roughness))

    def _step(self, state, seconds):
        old_thickness = state["thickness_nm"]
        actual_rate = (
            state["rate_command_nm_s"] * state["rate_gain"]
            if state["shutter"] == "open"
            else 0.0
        )
        deposited = actual_rate * seconds
        new_thickness = old_thickness + deposited
        if deposited > 0.0:
            state["porosity"] = (
                old_thickness * state["porosity"]
                + deposited * self.config["deposition_porosity"]
            ) / new_thickness
            state["roughness_nm"] += self.config["roughness_per_nm"] * deposited
            state["thickness_nm"] = new_thickness

        before_temperature = state["temperature_k"]
        target = state["temperature_setpoint_k"]
        tau = self.config["thermal_time"]
        state["temperature_k"] = target + (before_temperature - target) * math.exp(
            -seconds / tau
        )
        temperature = max(0.5 * (before_temperature + state["temperature_k"]), 1.0)
        anneal_rate = self.config["anneal_preexponential"] * math.exp(
            -self.config["anneal_activation"] / (R_GAS * temperature)
        )
        residual = self.config["residual_porosity"]
        state["porosity"] = residual + (state["porosity"] - residual) * math.exp(
            -anneal_rate * seconds
        )
        base = self.config["base_roughness"]
        state["roughness_nm"] = base + (state["roughness_nm"] - base) * math.exp(
            -0.5 * anneal_rate * seconds
        )
        state["time_s"] += seconds

    def advance(self, state, seconds):
        remaining = seconds
        while remaining > 1e-12:
            step = min(1.0, remaining)
            self._step(state, step)
            remaining -= step

    def perform(self, state, rng, action, params):
        if action == "deposition":
            state["rate_command_nm_s"] = params["rate"]
            self.advance(state, 0.05)
        elif action == "shutter":
            state["shutter"] = params["position"]
            self.advance(state, 0.05)
        elif action == "temperature":
            state["temperature_setpoint_k"] = params["setpoint"]
            self.advance(state, 0.1)
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            instrument = params["instrument"]
            duration = {"reflectometer": 1.0, "interferometer": 0.2, "pyrometer": 0.1}[
                instrument
            ]
            self.advance(state, duration)
            if instrument == "pyrometer":
                noise = 0.4
                return {
                    "temperature": reading(
                        state["temperature_k"] + rng.gauss(0.0, noise),
                        "K",
                        noise,
                        window_s=duration,
                    )
                }
            if instrument == "interferometer":
                wavelength = 632.8
                phase = (
                    4.0
                    * math.pi
                    * self.effective_index(state)
                    * state["thickness_nm"]
                    / wavelength
                ) % (2.0 * math.pi)
                visibility = math.exp(
                    -((4.0 * math.pi * state["roughness_nm"] / wavelength) ** 2)
                )
                return {
                    "phase": reading(
                        (phase + rng.gauss(0.0, 0.01)) % (2.0 * math.pi),
                        "rad",
                        0.01,
                        wavelength_nm=wavelength,
                        window_s=duration,
                    ),
                    "visibility": reading(
                        max(0.0, min(1.0, visibility + rng.gauss(0.0, 0.002))),
                        None,
                        0.002,
                        wavelength_nm=wavelength,
                        window_s=duration,
                    ),
                }
            noise = 0.0015
            values = [
                max(
                    0.0,
                    min(
                        1.0,
                        state["spectral_gain"] * self.reflectance(state, wavelength)
                        + state["spectral_offset"]
                        + rng.gauss(0.0, noise),
                    ),
                )
                for wavelength in WAVELENGTHS_NM
            ]
            return {
                "reflectance": {
                    "value": values,
                    "unit": None,
                    "noise_std": noise,
                    "shape": [len(WAVELENGTHS_NM)],
                    "axes": ["wavelength_nm"],
                    "axis_values": list(WAVELENGTHS_NM),
                    "window_s": duration,
                }
            }
        return {}

    def visible(self, state):
        return {
            "deposition_rate_nm_s": state["rate_command_nm_s"],
            "shutter": state["shutter"],
            "temperature_setpoint_k": state["temperature_setpoint_k"],
        }
