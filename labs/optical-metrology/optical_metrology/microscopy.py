"""Dose-limited fluorescence microscopy with focus, drift and photobleaching."""

import math

from synthetic_lab.model import Model, Parameter, reading
from synthetic_lab.research import ResearchContract

CHANNELS = {
    "green": {"wavelength_um": 0.520, "bleach_scale": 1.0},
    "red": {"wavelength_um": 0.630, "bleach_scale": 0.7},
}


class FluorescenceMicroscopy(Model):
    name = "fluorescence-microscopy"
    description = (
        "Choose focus, field position, spectral channel and photon dose while the sample drifts "
        "and fluorophores bleach."
    )
    defaults = {
        "numerical_aperture": 1.2,
        "pixel_size": 0.35,
        "pixels": 32,
        "background_rate": 18.0,
        "read_noise": 2.0,
        "camera_max": 65535.0,
        "drift": 0.002,
        "bleach": 0.035,
        "variation": 0.18,
    }
    parameters = {
        "numerical_aperture": Parameter(None, 0.2, 1.49),
        "pixel_size": Parameter("um", 0.05, 2.0),
        "pixels": Parameter(None, 16, 64),
        "background_rate": Parameter("count/s", 0.0, 1000.0),
        "read_noise": Parameter("count", 0.0, 100.0),
        "camera_max": Parameter("count", 255.0, 1.0e7),
        "drift": Parameter("um/s", 0.0, 0.05),
        "bleach": Parameter("1/mJ", 0.0, 2.0),
        "variation": Parameter(None, 0.0, 0.5),
    }
    actions = {
        "stage": {
            "x": Parameter("um", -20.0, 20.0),
            "y": Parameter("um", -20.0, 20.0),
        },
        "focus": {"z": Parameter("um", -5.0, 5.0)},
        "channel": {"name": Parameter(choices=tuple(CHANNELS))},
        "illumination": {"power": Parameter("mW", 0.0, 5.0)},
        "exposure": {"seconds": Parameter("s", 0.001, 1.0)},
        "read": {"instrument": Parameter(choices=("camera", "photometer"))},
        "wait": {"seconds": Parameter("s", 0.0, 3600.0)},
    }
    research = ResearchContract(
        domains=(
            "fluorescence microscopy",
            "cell biology",
            "scientific imaging",
            "optical metrology",
        ),
        phenomena=(
            "diffraction-limited image formation",
            "defocus",
            "spectral contrast",
            "sample drift",
            "photon statistics and read noise",
            "irreversible photobleaching",
        ),
        questions=(
            "Which focus and exposure schedule localizes structures with the least photon dose?",
            "When is a quick photometer reading preferable to a spatial image?",
            "How should stage motion compensate sample drift?",
            "Which spectral channel distinguishes rare red-dominant objects from green background?",
        ),
        observables={
            "image": {
                "unit": "count",
                "description": "A clipped two-dimensional camera image with finite pixel size.",
            },
            "total_fluorescence": {
                "unit": "count/s",
                "description": "A fast field-integrated fluorescence measurement.",
            },
        },
        latent_variables={
            "emitters": {
                "unit": None,
                "description": "Emitter positions, spectra and initial brightness.",
            },
            "focus_plane": {
                "unit": "um",
                "description": "Unknown sample plane relative to the objective command.",
            },
            "drift": {
                "unit": "um",
                "description": "Time-dependent lateral sample displacement.",
            },
            "remaining_fluorescence": {
                "unit": None,
                "description": "Emitter brightness retained after accumulated illumination dose.",
            },
        },
        interventions=("stage", "focus", "channel", "illumination", "exposure"),
        invariants=(
            "Remaining fluorophore brightness never increases after illumination.",
            "Camera counts remain within the configured detector range.",
            "All channels observe the same emitter positions and sample drift.",
        ),
        validity_conditions=(
            "Sparse independent emitters imaged by a Gaussian approximation to the PSF.",
            "Uniform illumination and a planar sample over one field of view.",
            "Gaussian approximation to photon and read noise.",
        ),
        limitations=(
            (
                "No scattering, out-of-focus background volume, blinking or nonlinear "
                "fluorophore states."
            ),
            "No cell growth, motion or morphology change beyond rigid sample drift.",
            "The optical response is generic rather than calibrated to a named microscope.",
        ),
        failure_conditions=(
            "Excess dose bleaches the signal needed by later measurements.",
            "Defocus broadens emitters until nearby structures cannot be separated.",
            "Drift can move the region of interest outside the camera field.",
        ),
        fidelity="reduced-order",
        action_semantics={
            "stage": {
                "kind": "control",
                "description": "Move the center of the camera field in the sample plane.",
            },
            "focus": {
                "kind": "control",
                "description": "Set the objective focus coordinate.",
            },
            "channel": {
                "kind": "configure",
                "description": "Select the fluorescence emission channel.",
            },
            "illumination": {
                "kind": "control",
                "description": "Set excitation power and therefore photon rate and bleach rate.",
            },
            "exposure": {
                "kind": "configure",
                "description": "Set the camera integration time.",
            },
            "read": {
                "kind": "measurement",
                "description": "Acquire a spatial camera image or fast integrated fluorescence.",
            },
            "wait": {
                "kind": "wait",
                "description": "Advance sample drift without illumination.",
            },
        },
        reference_methods=(
            "low-dose focus sweep",
            "image-gradient sharpness",
            "centroid drift tracking",
            "multi-channel emitter classification",
        ),
        physical_counterpart=(
            "A motorized widefield fluorescence microscope with camera and field photometer"
        ),
    )

    def initial(self, rng):
        variation = self.config["variation"]
        emitters = []
        for index in range(12):
            red_dominant = index in (0, 7)
            base = rng.uniform(900.0, 1500.0)
            emitters.append(
                {
                    "x_um": rng.uniform(-4.5, 4.5),
                    "y_um": rng.uniform(-4.5, 4.5),
                    "green": base * (0.35 if red_dominant else 1.0),
                    "red": base * (1.2 if red_dominant else 0.22),
                    "remaining": 1.0,
                }
            )
        angle = rng.uniform(0.0, 2.0 * math.pi)
        drift = self.config["drift"] * rng.uniform(1.0 - variation, 1.0 + variation)
        return {
            "time_s": 0.0,
            "stage_x_um": 0.0,
            "stage_y_um": 0.0,
            "focus_z_um": 0.0,
            "true_focus_um": rng.uniform(-1.5, 1.5),
            "channel": "green",
            "illumination_mw": 0.2,
            "exposure_s": 0.02,
            "drift_x_um": 0.0,
            "drift_y_um": 0.0,
            "drift_vx_um_s": drift * math.cos(angle),
            "drift_vy_um_s": drift * math.sin(angle),
            "gain": rng.uniform(1.0 - variation / 2.0, 1.0 + variation / 2.0),
            "offset": rng.uniform(2.0, 8.0),
            "emitters": emitters,
            "dose_mj": 0.0,
        }

    def advance(self, state, seconds):
        state["drift_x_um"] += state["drift_vx_um_s"] * seconds
        state["drift_y_um"] += state["drift_vy_um_s"] * seconds
        state["time_s"] += seconds

    def _sigma_pixels(self, state):
        wavelength = CHANNELS[state["channel"]]["wavelength_um"]
        diffraction = 0.21 * wavelength / self.config["numerical_aperture"]
        defocus = state["focus_z_um"] - state["true_focus_um"]
        sigma_um = math.sqrt(diffraction**2 + (0.38 * defocus) ** 2)
        return max(0.45, sigma_um / self.config["pixel_size"])

    def _expected_image(self, state):
        pixels = int(self.config["pixels"])
        sigma = self._sigma_pixels(state)
        exposure = state["exposure_s"]
        illumination = state["illumination_mw"]
        expected = [
            [self.config["background_rate"] * exposure + state["offset"] for _ in range(pixels)]
            for _ in range(pixels)
        ]
        center = (pixels - 1) / 2.0
        normalizer = 2.0 * math.pi * sigma**2
        for emitter in state["emitters"]:
            x = (
                emitter["x_um"]
                + state["drift_x_um"]
                - state["stage_x_um"]
            ) / self.config["pixel_size"] + center
            y = (
                emitter["y_um"]
                + state["drift_y_um"]
                - state["stage_y_um"]
            ) / self.config["pixel_size"] + center
            photons = (
                illumination
                * exposure
                * emitter[state["channel"]]
                * emitter["remaining"]
                * state["gain"]
            )
            radius = max(2, math.ceil(4.0 * sigma))
            for row in range(max(0, int(y) - radius), min(pixels, int(y) + radius + 1)):
                for column in range(
                    max(0, int(x) - radius), min(pixels, int(x) + radius + 1)
                ):
                    distance = (row - y) ** 2 + (column - x) ** 2
                    expected[row][column] += photons * math.exp(
                        -distance / (2.0 * sigma**2)
                    ) / normalizer
        return expected

    def _bleach(self, state, dose_mj):
        scale = CHANNELS[state["channel"]]["bleach_scale"]
        remaining = math.exp(-self.config["bleach"] * scale * dose_mj)
        for emitter in state["emitters"]:
            emitter["remaining"] *= remaining
        state["dose_mj"] += dose_mj

    def perform(self, state, rng, action, params):
        if action == "stage":
            state.update(stage_x_um=params["x"], stage_y_um=params["y"])
            self.advance(state, 0.15)
        elif action == "focus":
            state["focus_z_um"] = params["z"]
            self.advance(state, 0.1)
        elif action == "channel":
            state["channel"] = params["name"]
            self.advance(state, 0.05)
        elif action == "illumination":
            state["illumination_mw"] = params["power"]
            self.advance(state, 0.02)
        elif action == "exposure":
            state["exposure_s"] = params["seconds"]
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            instrument = params["instrument"]
            if instrument == "photometer":
                duration = 0.01
                self.advance(state, duration / 2.0)
                total = sum(
                    emitter[state["channel"]] * emitter["remaining"]
                    for emitter in state["emitters"]
                )
                rate = state["illumination_mw"] * total * state["gain"]
                noise = math.sqrt(max(rate * duration, 1.0)) / duration
                measured = max(0.0, rate + rng.gauss(0.0, noise))
                dose = state["illumination_mw"] * duration
                self._bleach(state, dose)
                self.advance(state, duration / 2.0)
                return {
                    "total_fluorescence": reading(
                        measured,
                        "count/s",
                        noise,
                        channel=state["channel"],
                        window_s=duration,
                        dose_mj=dose,
                    )
                }
            exposure = state["exposure_s"]
            self.advance(state, exposure / 2.0)
            expected = self._expected_image(state)
            image = []
            clipped = 0
            maximum = int(self.config["camera_max"])
            for line in expected:
                row = []
                for value in line:
                    standard = math.sqrt(value + self.config["read_noise"] ** 2)
                    count = round(rng.gauss(value, standard))
                    clipped += count >= maximum
                    row.append(max(0, min(maximum, count)))
                image.append(row)
            dose = state["illumination_mw"] * exposure
            self._bleach(state, dose)
            self.advance(state, exposure / 2.0)
            return {
                "image": {
                    "value": image,
                    "unit": "count",
                    "shape": [len(image), len(image[0])],
                    "axes": ["row", "column"],
                    "pixel_size_um": self.config["pixel_size"],
                    "channel": state["channel"],
                    "window_s": exposure,
                    "dose_mj": dose,
                    "saturated_pixels": clipped,
                    "noise_model": "Gaussian approximation to photon statistics plus read noise",
                }
            }
        return {}

    def visible(self, state):
        return {
            "stage_x_um": state["stage_x_um"],
            "stage_y_um": state["stage_y_um"],
            "focus_z_um": state["focus_z_um"],
            "channel": state["channel"],
            "illumination_mw": state["illumination_mw"],
            "exposure_s": state["exposure_s"],
            "accumulated_dose_mj": state["dose_mj"],
        }
