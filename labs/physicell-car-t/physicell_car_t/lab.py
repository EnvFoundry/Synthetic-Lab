"""Persistent solid-tumor CAR-T spheroid assays executed by PhysiCell."""

from __future__ import annotations

from synthetic_lab.model import Model, Parameter, reading

from .contract import contract
from .solver import run_assay


class CarTSpheroidLab(Model):
    name = "physicell-car-t-spheroid"
    version = "1"
    description = (
        "PhysiCell/BioFVM solid-tumor CAR-T spheroid with antigen heterogeneity, "
        "spatial infiltration, contact- and hypoxia-driven exhaustion and antigen escape."
    )
    defaults = {
        "tumor_radius_um": 60.0,
        "antigen_mean": 1.0,
        "antigen_sd": 0.30,
        "antigen_negative_fraction": 0.12,
        "antigen_loss_rate_per_min": 0.0015,
        "antigen_threshold": 0.35,
        "antigen_saturation": 1.50,
        "patient_variation": 0.08,
        "exhaustion_contact_rate_per_min": 0.0015,
        "exhaustion_hypoxia_rate_per_min": 0.0008,
        "exhaustion_recovery_rate_per_min": 0.0004,
        "kill_exhaustion_floor": 0.08,
        "motility_exhaustion_floor": 0.25,
        "hypoxia_threshold_mmhg": 10.0,
        "diffusion_dt_min": 0.08,
        "omp_threads": 2,
        "solver_timeout_s": 240.0,
    }
    parameters = {
        "tumor_radius_um": Parameter("um", 30.0, 180.0),
        "antigen_mean": Parameter(None, 0.0, 3.0),
        "antigen_sd": Parameter(None, 0.0, 1.5),
        "antigen_negative_fraction": Parameter(None, 0.0, 0.95),
        "antigen_loss_rate_per_min": Parameter("1/min", 0.0, 0.05),
        "antigen_threshold": Parameter(None, 0.0, 3.0),
        "antigen_saturation": Parameter(None, 0.01, 5.0),
        "patient_variation": Parameter(None, 0.0, 0.8),
        "exhaustion_contact_rate_per_min": Parameter("1/min", 0.0, 0.05),
        "exhaustion_hypoxia_rate_per_min": Parameter("1/min", 0.0, 0.05),
        "exhaustion_recovery_rate_per_min": Parameter("1/min", 0.0, 0.05),
        "kill_exhaustion_floor": Parameter(None, 0.0, 1.0),
        "motility_exhaustion_floor": Parameter(None, 0.0, 1.0),
        "hypoxia_threshold_mmhg": Parameter("mmHg", 0.0, 38.0),
        "diffusion_dt_min": Parameter("min", 0.01, 0.5),
        "omp_threads": Parameter(None, 1, 64),
        "solver_timeout_s": Parameter("s", 10.0, 7200.0),
    }
    actions = {
        "infuse": {
            "car_t_cells": Parameter("count", 0, 10000),
            "pre_growth_hours": Parameter("h", 0.0, 168.0),
            "treatment_hours": Parameter("h", 1.0, 168.0),
            "attachment_rate_per_min": Parameter("1/min", 0.0, 2.0),
            "dwell_time_min": Parameter("min", 0.25, 480.0),
            "kill_rate_per_min": Parameter("1/min", 0.0, 2.0),
            "motility_speed_um_min": Parameter(None, 0.05, 20.0),
        },
        "read": {
            "instrument": Parameter(choices=("tumor", "escape", "immune", "spatial", "summary"))
        },
        "snapshot": {},
    }
    research = contract()

    def initial(self, rng):
        variation = self.config["patient_variation"]

        def draw(value, lower=0.0, upper=None):
            result = value * (1.0 + rng.gauss(0.0, variation))
            result = max(lower, result)
            return min(upper, result) if upper is not None else result

        patient = {
            "antigen_mean": draw(
                self.config["antigen_mean"], 0.0, self.config["antigen_saturation"]
            ),
            "antigen_sd": draw(self.config["antigen_sd"], 0.0),
            "antigen_negative_fraction": draw(self.config["antigen_negative_fraction"], 0.0, 0.98),
            "antigen_loss_rate_per_min": draw(self.config["antigen_loss_rate_per_min"], 0.0),
            "exhaustion_scale": draw(1.0, 0.05, 5.0),
        }
        return {
            "time_s": 0.0,
            "solver_seed": rng.randrange(1, 2**31 - 1),
            "patient": patient,
            "protocol": None,
            "summary": None,
            "cells": None,
            "solve_count": 0,
        }

    def advance(self, state, seconds):
        if seconds:
            raise ValueError("CAR-T spheroid time advances only through infuse")

    def _settings(self):
        return {
            "tumor_radius_um": self.config["tumor_radius_um"],
            "antigen_threshold": self.config["antigen_threshold"],
            "antigen_saturation": self.config["antigen_saturation"],
            "exhaustion_contact_rate_per_min": self.config["exhaustion_contact_rate_per_min"],
            "exhaustion_hypoxia_rate_per_min": self.config["exhaustion_hypoxia_rate_per_min"],
            "exhaustion_recovery_rate_per_min": self.config["exhaustion_recovery_rate_per_min"],
            "kill_exhaustion_floor": self.config["kill_exhaustion_floor"],
            "motility_exhaustion_floor": self.config["motility_exhaustion_floor"],
            "hypoxia_threshold_mmhg": self.config["hypoxia_threshold_mmhg"],
            "diffusion_dt_min": self.config["diffusion_dt_min"],
            "omp_threads": int(self.config["omp_threads"]),
            "solver_timeout_s": self.config["solver_timeout_s"],
        }

    def _observations(self, state, instrument):
        if state["summary"] is None:
            raise ValueError("Infuse CAR-T cells before reading the co-culture endpoint")
        value = state["summary"]
        result = {}
        if instrument in ("tumor", "summary"):
            result.update(
                {
                    "tumor_total_cells": reading(value["tumor_total_cells"], "count"),
                    "tumor_viable_cells": reading(value["tumor_viable_cells"], "count"),
                    "tumor_viable_fraction": reading(value["tumor_viable_fraction"], None),
                    "tumor_apoptotic_fraction": reading(value["tumor_apoptotic_fraction"], None),
                    "tumor_necrotic_fraction": reading(value["tumor_necrotic_fraction"], None),
                    "equivalent_diameter": reading(value["equivalent_diameter_um"], "um"),
                    "mean_tumor_oxygen": reading(value["mean_tumor_oxygen_mmhg"], "mmHg"),
                }
            )
        if instrument in ("escape", "summary"):
            result.update(
                {
                    "antigen_low_viable_fraction": reading(
                        value["antigen_low_viable_fraction"], None
                    ),
                    "mean_viable_antigen": reading(value["mean_viable_antigen"], None),
                }
            )
        if instrument in ("immune", "summary"):
            result.update(
                {
                    "car_t_cells": reading(value["immune_cells"], "count"),
                    "mean_exhaustion": reading(value["mean_exhaustion"], None),
                    "exhausted_fraction": reading(value["exhausted_fraction"], None),
                    "engaged_fraction": reading(value["engaged_fraction"], None),
                    "total_contacts": reading(value["total_contacts"], "count"),
                    "total_kills": reading(value["total_kills"], "count"),
                }
            )
        if instrument in ("spatial", "summary"):
            result.update(
                {
                    "infiltrating_fraction": reading(value["infiltrating_fraction"], None),
                    "mean_infiltration_depth": reading(value["mean_infiltration_depth_um"], "um"),
                    "max_infiltration_depth": reading(value["max_infiltration_depth_um"], "um"),
                }
            )
        return result

    def perform(self, state, rng, action, params):
        del rng
        if action == "infuse":
            if state["protocol"] is not None:
                raise ValueError(
                    "This spheroid well has already received CAR-T cells; fork before infusion"
                )
            state["protocol"] = {
                "car_t_cells": int(params["car_t_cells"]),
                "pre_growth_hours": float(params["pre_growth_hours"]),
                "treatment_hours": float(params["treatment_hours"]),
                "attachment_rate_per_min": float(params["attachment_rate_per_min"]),
                "dwell_time_min": float(params["dwell_time_min"]),
                "kill_rate_per_min": float(params["kill_rate_per_min"]),
                "motility_speed_um_min": float(params["motility_speed_um_min"]),
            }
            solved = run_assay(
                seed=state["solver_seed"],
                protocol=state["protocol"],
                patient=state["patient"],
                settings=self._settings(),
            )
            state["summary"] = solved["summary"]
            state["cells"] = solved["cells"]
            state["time_s"] += 3600.0 * (
                state["protocol"]["pre_growth_hours"] + state["protocol"]["treatment_hours"]
            )
            state["solve_count"] += 1
            return self._observations(state, "summary")
        if action == "read":
            return self._observations(state, params["instrument"])
        if action == "snapshot":
            if state["cells"] is None:
                raise ValueError("Infuse CAR-T cells before acquiring a cell map")
            count = len(state["cells"]["x_um"])
            return {
                "cell_map": {
                    "value": state["cells"],
                    "unit": None,
                    "shape": [count],
                    "axes": ["cell"],
                    "fields": {
                        "cell_type": None,
                        "x_um": "um",
                        "y_um": "um",
                        "z_um": "um",
                        "dead": None,
                        "apoptotic": None,
                        "necrotic": None,
                        "car_antigen": None,
                        "oxygen_mmhg": "mmHg",
                        "exhaustion": None,
                        "engaged": None,
                        "contact_events": "count",
                        "kills": "count",
                    },
                }
            }
        return {}

    def visible(self, state):
        protocol = state["protocol"] or {}
        return {
            "solver_backend": "PhysiCell 1.14.2 with BioFVM",
            "geometry": "three-dimensional avascular spheroid",
            "infused": state["protocol"] is not None,
            "car_t_cells": protocol.get("car_t_cells", 0),
            "dwell_time_min": protocol.get("dwell_time_min", 0.0),
            "elapsed_h": state["time_s"] / 3600.0,
            "solver_runs": state["solve_count"],
        }
