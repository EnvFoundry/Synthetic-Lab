"""Persistent full-wave spectroscopy of a fabricated photonic-crystal cavity."""

from __future__ import annotations

import math

from synthetic_lab.model import Model, Parameter, reading

from .contract import cavity_contract
from .solver import resonance_summary, resonant_field, transmission_spectrum


class MeepPhotonicCavity(Model):
    name = "meep-photonic-cavity"
    version = "2"
    description = (
        "A fabricated photonic-crystal waveguide cavity measured by Meep broadband "
        "transmission spectroscopy and resonant field imaging."
    )
    defaults = {
        "hole_radius": 0.36,
        "defect_spacing": 1.40,
        "hole_radius_sigma": 0.003,
        "defect_spacing_sigma": 0.006,
        "holes_per_side": 2.0,
        "waveguide_epsilon": 13.0,
        "waveguide_width": 1.20,
        "center_frequency": 0.25,
        "frequency_width": 0.16,
        "frequency_points": 31.0,
        "resolution": 10.0,
        "decay_time": 60.0,
        "field_run_time": 40.0,
        "spectrometer_noise": 0.002,
        "fabrication_time": 3600.0,
        "spectrum_time": 5.0,
        "field_time": 20.0,
    }
    parameters = {
        "hole_radius": Parameter("um", 0.20, 0.50),
        "defect_spacing": Parameter("um", 1.0, 2.0),
        "hole_radius_sigma": Parameter("um", 0.0, 0.05),
        "defect_spacing_sigma": Parameter("um", 0.0, 0.10),
        "holes_per_side": Parameter(None, 1.0, 6.0),
        "waveguide_epsilon": Parameter(None, 2.0, 20.0),
        "waveguide_width": Parameter("um", 0.5, 3.0),
        "center_frequency": Parameter("1/um", 0.10, 0.60),
        "frequency_width": Parameter("1/um", 0.02, 0.40),
        "frequency_points": Parameter(None, 9.0, 201.0),
        "resolution": Parameter("pixel/um", 6.0, 40.0),
        "decay_time": Parameter(None, 10.0, 400.0),
        "field_run_time": Parameter(None, 5.0, 200.0),
        "spectrometer_noise": Parameter(None, 0.0, 0.05),
        "fabrication_time": Parameter("s", 0.0, 86400.0),
        "spectrum_time": Parameter("s", 0.0, 3600.0),
        "field_time": Parameter("s", 0.0, 3600.0),
    }
    actions = {
        "design": {
            "hole_radius": Parameter("um", 0.20, 0.50),
            "defect_spacing": Parameter("um", 1.0, 2.0),
        },
        "fabricate": {},
        "measure": {"instrument": Parameter(choices=("spectrum", "resonance", "summary", "field"))},
    }
    research = cavity_contract()

    def __init__(self, config=None):
        super().__init__(config)
        for name in ("holes_per_side", "frequency_points", "resolution"):
            rounded = round(self.config[name])
            if not math.isclose(self.config[name], rounded, abs_tol=1e-9):
                raise ValueError(f"{name} must be an integer")
            self.config[name] = int(rounded)
        if self.config["frequency_width"] >= 2.0 * self.config["center_frequency"]:
            raise ValueError("frequency_width must keep the source band above zero")

    def initial(self, rng):
        del rng
        return {
            "time_s": 0.0,
            "design_hole_radius_um": self.config["hole_radius"],
            "design_defect_spacing_um": self.config["defect_spacing"],
            "fabricated": False,
            "actual_hole_radius_um": None,
            "actual_defect_spacing_um": None,
            "spectrum": None,
            "resonance": None,
            "field": None,
            "solver_runs": 0,
            "measurements": 0,
        }

    def advance(self, state, seconds):
        state["time_s"] += seconds

    def _clear_results(self, state):
        state["spectrum"] = None
        state["resonance"] = None
        state["field"] = None

    def _ensure_fabricated(self, state):
        if not state["fabricated"]:
            raise ValueError("Fabricate the device before measuring it")

    def _ensure_spectrum(self, state):
        if state["spectrum"] is not None:
            return
        state["spectrum"] = transmission_spectrum(
            hole_radius=state["actual_hole_radius_um"],
            defect_spacing=state["actual_defect_spacing_um"],
            holes_per_side=self.config["holes_per_side"],
            epsilon=self.config["waveguide_epsilon"],
            waveguide_width=self.config["waveguide_width"],
            center_frequency=self.config["center_frequency"],
            frequency_width=self.config["frequency_width"],
            frequency_points=self.config["frequency_points"],
            resolution=self.config["resolution"],
            decay_time=self.config["decay_time"],
        )
        state["solver_runs"] += 2

    def _noisy_spectrum(self, state, rng):
        noise = self.config["spectrometer_noise"]
        return {
            **state["spectrum"],
            "transmission": [
                max(0.0, value + rng.gauss(0.0, noise))
                for value in state["spectrum"]["transmission"]
            ],
        }

    def _spectrum_observation(self, spectrum):
        return {
            "transmission_spectrum": {
                "value": spectrum["transmission"],
                "unit": None,
                "noise_std": self.config["spectrometer_noise"],
                "shape": [len(spectrum["transmission"])],
                "axes": ["wavelength_um"],
                "axis_values": spectrum["wavelength_um"],
                "frequency_inverse_um": spectrum["frequency_inverse_um"],
                "normalization": "straight-waveguide reference",
                "solver_backend": "Meep",
            }
        }

    def _summary_observations(self, summary):
        quality = summary["quality_factor"]
        return {
            "resonance_wavelength": reading(
                summary["resonance_wavelength_um"],
                "um",
                extraction="quadratic fit around the central-band transmission maximum",
                sampled_wavelength_um=summary["sampled_resonance_wavelength_um"],
                interpolated=summary["resonance_interpolated"],
            ),
            "peak_transmission": reading(summary["peak_transmission"], None),
            "spectral_contrast": reading(summary["spectral_contrast"], None),
            "quality_factor": {
                "value": quality,
                "unit": None,
                "resolved": quality is not None,
            },
        }

    def perform(self, state, rng, action, params):
        if action == "design":
            if state["fabricated"]:
                raise ValueError("Fork the pre-fabrication state to compare another design")
            state["design_hole_radius_um"] = params["hole_radius"]
            state["design_defect_spacing_um"] = params["defect_spacing"]
            self._clear_results(state)
            return {}

        if action == "fabricate":
            if state["fabricated"]:
                raise ValueError("This session already contains a fabricated sample")
            state["actual_hole_radius_um"] = state["design_hole_radius_um"] + rng.gauss(
                0.0, self.config["hole_radius_sigma"]
            )
            state["actual_defect_spacing_um"] = state["design_defect_spacing_um"] + rng.gauss(
                0.0, self.config["defect_spacing_sigma"]
            )
            if not 0.0 < state["actual_hole_radius_um"] < 0.5 * self.config["waveguide_width"]:
                raise ValueError("Fabricated hole radius is outside the represented geometry")
            state["fabricated"] = True
            self._clear_results(state)
            self.advance(state, self.config["fabrication_time"])
            return {}

        if action == "measure":
            self._ensure_fabricated(state)
            instrument = params["instrument"]
            state["measurements"] += 1

            if instrument == "field":
                if state["resonance"] is None:
                    raise ValueError("Measure a spectrum or resonance before field imaging")
                if state["field"] is None:
                    state["field"] = resonant_field(
                        hole_radius=state["actual_hole_radius_um"],
                        defect_spacing=state["actual_defect_spacing_um"],
                        holes_per_side=self.config["holes_per_side"],
                        epsilon=self.config["waveguide_epsilon"],
                        waveguide_width=self.config["waveguide_width"],
                        frequency=state["resonance"]["resonance_frequency_inverse_um"],
                        resolution=self.config["resolution"],
                        run_time=self.config["field_run_time"],
                    )
                    state["solver_runs"] += 1
                self.advance(state, self.config["field_time"])
                return {
                    "field_intensity": {
                        "value": state["field"]["value"],
                        "unit": "a.u.",
                        "shape": state["field"]["shape"],
                        "axes": ["x_um", "y_um"],
                        "extent_um": state["field"]["extent_um"],
                        "normalization": "maximum intensity equals one",
                        "sampling": "finite-time complex-field intensity",
                        "run_time_meep": self.config["field_run_time"],
                        "frequency_inverse_um": state["resonance"][
                            "resonance_frequency_inverse_um"
                        ],
                    }
                }

            self._ensure_spectrum(state)
            noisy = self._noisy_spectrum(state, rng)
            summary = resonance_summary(
                noisy,
                self.config["center_frequency"],
                self.config["frequency_width"],
            )
            if state["resonance"] != summary:
                state["field"] = None
            state["resonance"] = summary
            self.advance(state, self.config["spectrum_time"])
            if instrument == "spectrum":
                return self._spectrum_observation(noisy)
            if instrument == "resonance":
                return self._summary_observations(summary)
            observations = self._spectrum_observation(noisy)
            observations.update(self._summary_observations(summary))
            return observations

        return {}

    def visible(self, state):
        return {
            "solver_backend": "Meep",
            "geometry": "two-dimensional photonic-crystal waveguide cavity",
            "design_hole_radius_um": state["design_hole_radius_um"],
            "design_defect_spacing_um": state["design_defect_spacing_um"],
            "fabricated": state["fabricated"],
            "resolution_pixel_per_um": self.config["resolution"],
            "holes_per_side": self.config["holes_per_side"],
            "source_band_inverse_um": [
                self.config["center_frequency"] - 0.5 * self.config["frequency_width"],
                self.config["center_frequency"] + 0.5 * self.config["frequency_width"],
            ],
            "solver_runs": state["solver_runs"],
            "measurements": state["measurements"],
        }
