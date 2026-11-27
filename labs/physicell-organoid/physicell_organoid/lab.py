"""Persistent tumor-organoid treatment assays executed by PhysiCell."""

from __future__ import annotations

from synthetic_lab.model import Model, Parameter, reading

from .contract import contract
from .solver import run_assay


class TumorOrganoidLab(Model):
    name = "physicell-tumor-organoid"
    version = "2"
    description = (
        "PhysiCell/BioFVM tumor-organoid assay with oxygen limitation, treatment penetration, "
        "damage repair and seeded resistant subpopulations."
    )
    defaults = {
        "tumor_radius_um": 80.0,
        "resistant_fraction_mean": 0.12,
        "resistant_fraction_sd": 0.035,
        "sensitive_damage_rate": 0.03333,
        "resistant_damage_ratio": 0.45,
        "sensitive_repair_rate": 0.004167,
        "resistant_repair_ratio": 2.5,
        "drug_death_rate": 0.004167,
        "damage_scale": 8.0,
        "patient_variation": 0.12,
        "hypoxia_threshold_mmhg": 10.0,
        "diffusion_dt_min": 0.05,
        "omp_threads": 1,
        "solver_timeout_s": 180.0,
    }
    parameters = {
        "tumor_radius_um": Parameter("um", 30.0, 300.0),
        "resistant_fraction_mean": Parameter(None, 0.0, 0.95),
        "resistant_fraction_sd": Parameter(None, 0.0, 0.40),
        "sensitive_damage_rate": Parameter(None, 1e-5, 1.0),
        "resistant_damage_ratio": Parameter(None, 0.01, 1.0),
        "sensitive_repair_rate": Parameter(None, 0.0, 0.2),
        "resistant_repair_ratio": Parameter(None, 1.0, 20.0),
        "drug_death_rate": Parameter(None, 1e-6, 0.2),
        "damage_scale": Parameter(None, 1e-6, 1000.0),
        "patient_variation": Parameter(None, 0.0, 0.8),
        "hypoxia_threshold_mmhg": Parameter("mmHg", 0.0, 38.0),
        "diffusion_dt_min": Parameter("min", 0.005, 0.1),
        "omp_threads": Parameter(None, 1, 64),
        "solver_timeout_s": Parameter("s", 10.0, 7200.0),
    }
    actions = {
        "expose": {
            "concentration": Parameter(None, 0.0, 5.0),
            "pre_culture_hours": Parameter("h", 0.0, 168.0),
            "exposure_hours": Parameter("h", 1.0, 168.0),
            "recovery_hours": Parameter("h", 0.0, 168.0),
        },
        "read": {
            "instrument": Parameter(
                choices=("viability", "hypoxia", "resistance", "morphology", "summary")
            )
        },
        "snapshot": {},
    }
    research = contract()

    def __init__(self, config=None):
        super().__init__(config)
        if int(self.config["omp_threads"]) != self.config["omp_threads"]:
            raise ValueError("omp_threads must be an integer")

    def initial(self, rng):
        variation = self.config["patient_variation"]

        def draw(value, lower=0.0):
            return max(lower, value * (1.0 + rng.gauss(0.0, variation)))

        resistant_fraction = min(
            0.98,
            max(
                0.0,
                rng.gauss(
                    self.config["resistant_fraction_mean"],
                    self.config["resistant_fraction_sd"],
                ),
            ),
        )
        sensitive_damage = draw(self.config["sensitive_damage_rate"], 1e-8)
        sensitive_repair = draw(self.config["sensitive_repair_rate"], 0.0)
        return {
            "time_s": 0.0,
            "solver_seed": rng.randrange(1, 2**31 - 1),
            "patient": {
                "resistant_fraction": resistant_fraction,
                "sensitive_damage_rate": sensitive_damage,
                "resistant_damage_rate": sensitive_damage * self.config["resistant_damage_ratio"],
                "sensitive_repair_rate": sensitive_repair,
                "resistant_repair_rate": sensitive_repair * self.config["resistant_repair_ratio"],
                "drug_death_rate": draw(self.config["drug_death_rate"], 1e-8),
            },
            "protocol": None,
            "summary": None,
            "cells": None,
            "solve_count": 0,
        }

    def advance(self, state, seconds):
        if seconds:
            raise ValueError("Tumor-organoid time advances only through expose")

    def _settings(self):
        return {
            "tumor_radius_um": self.config["tumor_radius_um"],
            "damage_scale": self.config["damage_scale"],
            "hypoxia_threshold_mmhg": self.config["hypoxia_threshold_mmhg"],
            "diffusion_dt_min": self.config["diffusion_dt_min"],
            "omp_threads": int(self.config["omp_threads"]),
            "solver_timeout_s": self.config["solver_timeout_s"],
        }

    def _observations(self, state, instrument):
        if state["summary"] is None:
            raise ValueError("Expose the organoid before reading the endpoint")
        value = state["summary"]
        result = {}
        if instrument in ("viability", "summary"):
            result.update(
                {
                    "total_cells": reading(value["total_cells"], "count"),
                    "viable_cells": reading(value["viable_cells"], "count"),
                    "viable_fraction": reading(value["viable_fraction"], None),
                    "apoptotic_fraction": reading(value["apoptotic_fraction"], None),
                    "necrotic_fraction": reading(value["necrotic_fraction"], None),
                    "mean_damage": reading(value["mean_damage"], None),
                }
            )
        if instrument in ("hypoxia", "summary"):
            result.update(
                {
                    "hypoxic_viable_fraction": reading(value["hypoxic_viable_fraction"], None),
                    "mean_oxygen": reading(value["mean_oxygen_mmhg"], "mmHg"),
                }
            )
        if instrument in ("resistance", "summary"):
            result["resistant_viable_cells"] = reading(value["resistant_viable_cells"], "count")
            result["resistant_viable_fraction"] = reading(value["resistant_viable_fraction"], None)
        if instrument in ("morphology", "summary"):
            result["equivalent_diameter"] = reading(value["equivalent_diameter_um"], "um")
        if instrument == "summary":
            result.update(
                {
                    "mean_therapeutic": reading(value["mean_therapeutic"], None),
                    "treatment_auc": reading(
                        state["protocol"]["concentration"] * state["protocol"]["exposure_hours"],
                        "h",
                        concentration_unit="dimensionless",
                    ),
                }
            )
        return result

    def perform(self, state, rng, action, params):
        del rng
        if action == "expose":
            if state["protocol"] is not None:
                raise ValueError("This assay well has already been exposed; fork before treatment")
            state["protocol"] = {key: float(value) for key, value in params.items()}
            solved = run_assay(
                seed=state["solver_seed"],
                protocol=state["protocol"],
                patient=state["patient"],
                settings=self._settings(),
            )
            state["summary"] = solved["summary"]
            state["cells"] = solved["cells"]
            state["time_s"] = 60.0 * solved["summary"]["elapsed_min"]
            state["solve_count"] += 1
            return self._observations(state, "summary")
        if action == "read":
            return self._observations(state, params["instrument"])
        if action == "snapshot":
            if state["cells"] is None:
                raise ValueError("Expose the organoid before acquiring a cell map")
            count = len(state["cells"]["x_um"])
            return {
                "cell_map": {
                    "value": state["cells"],
                    "unit": None,
                    "shape": [count],
                    "axes": ["cell"],
                    "fields": {
                        "x_um": "um",
                        "y_um": "um",
                        "z_um": "um",
                        "dead": None,
                        "apoptotic": None,
                        "necrotic": None,
                        "resistant": None,
                        "oxygen_mmhg": "mmHg",
                        "therapeutic": None,
                        "damage": None,
                    },
                }
            }
        return {}

    def visible(self, state):
        protocol = state["protocol"] or {}
        return {
            "solver_backend": "PhysiCell 1.14.2 with BioFVM",
            "geometry": "two-dimensional organoid section",
            "exposed": state["protocol"] is not None,
            "concentration": protocol.get("concentration", 0.0),
            "elapsed_h": state["time_s"] / 3600.0,
            "solver_runs": state["solve_count"],
        }
