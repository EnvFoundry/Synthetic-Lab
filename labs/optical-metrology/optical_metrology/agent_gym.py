"""Verifiable optical experiment-design tasks."""

import copy
import json
import math
import random

from agent_gym.contracts import Task, Tool, Verdict, number, object_schema

from synthetic_lab import Lab
from synthetic_lab.model import Parameter

from .microscopy import FluorescenceMicroscopy
from .thin_film import WAVELENGTHS_NM, ThinFilmBench


def _tool(model, name, description, parameters=None):
    specification = model.actions[name] if parameters is None else parameters
    return Tool(
        name,
        description,
        object_schema(
            {key: parameter.describe() for key, parameter in specification.items()},
            list(specification),
        ),
    )


class _OwnedExperiment:
    def _hidden_state(self):
        with self.lab._lock:
            row = self.lab._row(self.session.id)
            return json.loads(row["state"])

    def close(self):
        self.lab.close()


class ThinFilmEndpointExperiment(_OwnedExperiment):
    """Control an uncertain deposition rate from optical endpoint measurements."""

    def __init__(self, seed, target_thickness_nm, variation):
        self.model = ThinFilmBench({"variation": variation})
        initial = self.model.initial(random.Random(seed))
        target = copy.deepcopy(initial)
        target["thickness_nm"] = target_thickness_nm
        target["porosity"] = self.model.config["deposition_porosity"]
        target["roughness_nm"] = (
            self.model.config["base_roughness"]
            + self.model.config["roughness_per_nm"] * target_thickness_nm
        )
        target["shutter"] = "closed"
        self.target_thickness_nm = target_thickness_nm
        self.target_phase_rad = self._phase(target)
        self.target_reflectance = self._ideal_spectrum(target)

        self.lab = Lab(":memory:")
        self.session = self.lab.create("thin-film", seed=seed, config={"variation": variation})
        self.tools = (
            _tool(
                self.model,
                "deposition",
                "Set the nominal deposition rate in nm/s; the actual specimen rate is uncertain.",
            ),
            _tool(self.model, "shutter", "Open or close material deposition."),
            _tool(
                self.model,
                "read",
                "Acquire broadband reflectance, single-wavelength phase, or temperature.",
            ),
            _tool(self.model, "wait", "Advance film growth for a chosen number of seconds."),
        )
        self._allowed = {tool.name for tool in self.tools}

    def _phase(self, state):
        return (
            4.0 * math.pi * self.model.effective_index(state) * state["thickness_nm"] / 632.8
        ) % (2.0 * math.pi)

    def _ideal_spectrum(self, state):
        return [
            max(
                0.0,
                min(
                    1.0,
                    state["spectral_gain"] * self.model.reflectance(state, wavelength)
                    + state["spectral_offset"],
                ),
            )
            for wavelength in WAVELENGTHS_NM
        ]

    def call(self, name, arguments):
        if name not in self._allowed:
            raise ValueError("This task permits deposition, shutter, read and wait")
        return self.session.act(name, **arguments)

    def endpoint_metrics(self):
        state = self._hidden_state()
        spectrum = self._ideal_spectrum(state)
        spectral_rmse = math.sqrt(
            sum(
                (measured - target) ** 2
                for measured, target in zip(spectrum, self.target_reflectance)
            )
            / len(spectrum)
        )
        phase_error = abs(self._phase(state) - self.target_phase_rad)
        phase_error = min(phase_error, 2.0 * math.pi - phase_error)
        return {
            "thickness_error_nm": abs(state["thickness_nm"] - self.target_thickness_nm),
            "phase_error_rad": phase_error,
            "spectral_rmse": spectral_rmse,
            "shutter_closed": state["shutter"] == "closed",
        }


class MicroscopyFocusExperiment(_OwnedExperiment):
    """Estimate the specimen plane while limiting irreversible illumination dose."""

    def __init__(self, seed, difficulty):
        configurations = {
            1: {"variation": 0.0, "drift": 0.0, "read_noise": 1.0, "background_rate": 5.0},
            2: {"variation": 0.08, "drift": 0.002, "read_noise": 1.5, "background_rate": 12.0},
            3: {"variation": 0.18, "drift": 0.004, "read_noise": 2.0, "background_rate": 18.0},
        }
        self.config = configurations[difficulty]
        self.model = FluorescenceMicroscopy(self.config)
        initial = self.model.initial(random.Random(seed))
        self.true_focus_um = initial["true_focus_um"]
        self.focus_tolerance_um = 0.40
        self.dose_budget_mj = {1: 0.24, 2: 0.22, 3: 0.20}[difficulty]

        self.lab = Lab(":memory:")
        self.session = self.lab.create("fluorescence-microscopy", seed=seed, config=self.config)
        camera_only = {"instrument": Parameter(choices=("camera",))}
        self.tools = (
            _tool(self.model, "focus", "Set the objective focus coordinate in micrometres."),
            _tool(self.model, "illumination", "Set excitation power in milliwatts."),
            _tool(self.model, "exposure", "Set camera exposure time in seconds."),
            _tool(
                self.model,
                "read",
                "Acquire a fluorescence camera image. Use instrument='camera'.",
                camera_only,
            ),
        )
        self._allowed = {tool.name for tool in self.tools}

    def call(self, name, arguments):
        if name not in self._allowed:
            raise ValueError("This task permits focus, illumination, exposure and camera read")
        if name == "read" and arguments.get("instrument") != "camera":
            raise ValueError("This task exposes only the camera")
        return self.session.act(name, **arguments)

    def focus_metrics(self, estimate):
        state = self._hidden_state()
        return {
            "absolute_focus_error_um": abs(estimate - self.true_focus_um),
            "accumulated_dose_mj": state["dose_mj"],
        }


def make_thin_film_endpoint(spec):
    if spec.family != "synthetic-thin-film-endpoint" or spec.version != 1:
        raise ValueError("synthetic-thin-film-endpoint supports task version 1")
    rng = spec.rng()
    ranges = {1: (55.0, 90.0), 2: (65.0, 110.0), 3: (45.0, 125.0)}
    variation = {1: 0.03, 2: 0.06, 3: 0.10}[spec.difficulty]
    target_thickness = rng.uniform(*ranges[spec.difficulty])
    environment = ThinFilmEndpointExperiment(rng.randrange(2**63), target_thickness, variation)

    def verify(answer):
        try:
            if answer != {"complete": True}:
                raise ValueError("Submit {complete: true} after closing the deposition shutter")
            metrics = environment.endpoint_metrics()
            passed = (
                metrics["shutter_closed"]
                and metrics["phase_error_rad"] <= 0.12
                and metrics["spectral_rmse"] <= 0.015
            )
            phase_score = max(0.0, 1.0 - metrics["phase_error_rad"] / 0.30)
            spectral_score = max(0.0, 1.0 - metrics["spectral_rmse"] / 0.04)
            reward = (
                (0.55 * phase_score + 0.45 * spectral_score) if metrics["shutter_closed"] else 0.0
            )
            return Verdict(
                passed,
                reward,
                "Final optical endpoint compared with the target phase and spectrum",
                metrics,
            )
        except ValueError as exc:
            return Verdict(False, 0.0, str(exc))

    spectrum = ", ".join(f"{value:.6f}" for value in environment.target_reflectance)
    prompt = (
        "Grow a single optical film from zero thickness to the requested endpoint. The actual "
        "growth rate differs from the commanded rate. Use phase interferometry for fine control "
        "and broadband reflectometry to distinguish an incorrect endpoint. The target phase at "
        f"632.8 nm is {environment.target_phase_rad:.6f} rad. Target reflectance at "
        f"{list(WAVELENGTHS_NM)} nm is [{spectrum}]. Close the shutter before submitting "
        "{complete: true}. All observations are simulated."
    )
    return Task(
        spec,
        prompt,
        environment,
        verify,
        max_actions={1: 40, 2: 46, 3: 52}[spec.difficulty],
    )


def make_microscopy_focus(spec):
    if spec.family != "synthetic-microscopy-focus" or spec.version != 1:
        raise ValueError("synthetic-microscopy-focus supports task version 1")
    rng = spec.rng()
    environment = MicroscopyFocusExperiment(rng.randrange(2**63), spec.difficulty)

    def verify(answer):
        try:
            if not isinstance(answer, dict) or set(answer) != {"focus_z_um"}:
                raise ValueError("Submit {focus_z_um: number}")
            estimate = number(answer["focus_z_um"], "focus_z_um")
            metrics = environment.focus_metrics(estimate)
            error = metrics["absolute_focus_error_um"]
            dose = metrics["accumulated_dose_mj"]
            passed = error <= environment.focus_tolerance_um and dose <= environment.dose_budget_mj
            focus_score = max(0.0, 1.0 - error / 1.2)
            dose_score = max(0.0, 1.0 - dose / (2.0 * environment.dose_budget_mj))
            reward = 0.8 * focus_score + 0.2 * dose_score
            return Verdict(
                passed,
                reward,
                "Submitted focus compared with the specimen plane and accumulated photon dose",
                metrics,
            )
        except ValueError as exc:
            return Verdict(False, 0.0, str(exc))

    prompt = (
        "Estimate the specimen focus plane in micrometres from fluorescence camera images. "
        "Choose focus positions, illumination and exposure. Illumination irreversibly consumes "
        f"signal. Submit {{focus_z_um: number}} with absolute error at most "
        f"{environment.focus_tolerance_um:.2f} um while keeping accumulated dose at or below "
        f"{environment.dose_budget_mj:.2f} mJ. The true focus lies between -1.5 and 1.5 um. "
        "All observations are simulated."
    )
    return Task(spec, prompt, environment, verify, max_actions=32)
