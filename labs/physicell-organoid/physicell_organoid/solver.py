"""Run and read the external PhysiCell organoid project."""

from __future__ import annotations

import csv
import math
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

_EXECUTABLE_ENV = "PHYSICELL_ORGANOID_EXECUTABLE"
_CONFIG_ENV = "PHYSICELL_ORGANOID_CONFIG"


def _finite(value, name):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"PhysiCell returned a non-finite {name}")
    return result


def _executable():
    raw = os.environ.get(_EXECUTABLE_ENV)
    if not raw:
        raise FileNotFoundError(
            f"Set {_EXECUTABLE_ENV} to the compiled organoid_therapy executable"
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"PhysiCell executable does not exist: {path}")
    return path


def _base_config(executable):
    raw = os.environ.get(_CONFIG_ENV)
    path = (
        Path(raw).expanduser().resolve()
        if raw
        else executable.parent / "config" / "PhysiCell_settings.xml"
    )
    if not path.is_file():
        raise FileNotFoundError(f"PhysiCell organoid configuration does not exist: {path}")
    return path


def _required(root, path):
    node = root.find(path)
    if node is None:
        raise ValueError(f"Missing PhysiCell configuration node: {path}")
    return node


def _set(root, path, value):
    _required(root, path).text = str(value)


def _user_parameter(root, name, value, kind="double", units="none"):
    parent = _required(root, "./user_parameters")
    node = parent.find(name)
    if node is None:
        node = ET.SubElement(parent, name, {"type": kind, "units": units, "description": ""})
    node.text = str(value)


def _therapeutic_boundaries(root):
    for variable in root.findall("./microenvironment_setup/variable"):
        if variable.get("name") != "therapeutic":
            continue
        condition = _required(variable, "./Dirichlet_boundary_condition")
        condition.set("enabled", "True")
        condition.text = "0"
        for boundary in variable.findall("./Dirichlet_options/boundary_value"):
            boundary.set(
                "enabled",
                "True" if boundary.get("ID") in {"xmin", "xmax", "ymin", "ymax"} else "False",
            )
            boundary.text = "0"
        return
    raise ValueError("The PhysiCell configuration has no therapeutic substrate")


def _write_config(path, output, seed, protocol, patient, settings):
    tree = ET.parse(path)
    root = tree.getroot()
    total_minutes = 60.0 * (
        protocol["pre_culture_hours"] + protocol["exposure_hours"] + protocol["recovery_hours"]
    )
    start_minutes = 60.0 * protocol["pre_culture_hours"]
    end_minutes = start_minutes + 60.0 * protocol["exposure_hours"]

    half_width = max(150.0, settings["tumor_radius_um"] + 100.0)
    _set(root, "./domain/x_min", -half_width)
    _set(root, "./domain/x_max", half_width)
    _set(root, "./domain/y_min", -half_width)
    _set(root, "./domain/y_max", half_width)
    _set(root, "./overall/max_time", total_minutes)
    _set(root, "./overall/dt_diffusion", settings["diffusion_dt_min"])
    _set(root, "./parallel/omp_num_threads", settings["omp_threads"])
    _set(root, "./save/folder", output.as_posix())
    _set(root, "./save/full_data/enable", "false")
    _set(root, "./save/SVG/enable", "false")
    _set(root, "./options/random_seed", seed)
    _therapeutic_boundaries(root)
    custom = _required(root, './cell_definitions/cell_definition[@name="cancer cell"]/custom_data')
    ET.SubElement(custom, "resistant", {"units": "dimensionless"}).text = "0"

    _user_parameter(root, "number_of_cells", 0, kind="int")
    _user_parameter(root, "number_of_injected_cells", 0, kind="int")
    _user_parameter(root, "therapy_activation_time", total_minutes + 1.0)
    _user_parameter(root, "save_interval_after_therapy_start", total_minutes + 1.0)
    _user_parameter(root, "tumor_radius", settings["tumor_radius_um"], units="um")
    _user_parameter(root, "treatment_start_min", start_minutes, units="min")
    _user_parameter(root, "treatment_end_min", end_minutes, units="min")
    _user_parameter(root, "treatment_concentration", protocol["concentration"])
    _user_parameter(root, "resistant_fraction", patient["resistant_fraction"])
    _user_parameter(root, "sensitive_damage_rate", patient["sensitive_damage_rate"])
    _user_parameter(root, "resistant_damage_rate", patient["resistant_damage_rate"])
    _user_parameter(root, "sensitive_repair_rate", patient["sensitive_repair_rate"])
    _user_parameter(root, "resistant_repair_rate", patient["resistant_repair_rate"])
    _user_parameter(root, "drug_death_rate", patient["drug_death_rate"])
    _user_parameter(root, "damage_scale", settings["damage_scale"])
    _user_parameter(
        root,
        "hypoxia_threshold",
        settings["hypoxia_threshold_mmhg"],
        units="mmHg",
    )

    config = output.parent / "PhysiCell_settings.xml"
    tree.write(config, encoding="utf-8", xml_declaration=True)
    return config


def _summary(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError("PhysiCell summary must contain exactly one result row")
    row = rows[0]
    integer_fields = {
        "total_cells",
        "viable_cells",
        "apoptotic_cells",
        "necrotic_cells",
        "resistant_viable_cells",
        "hypoxic_viable_cells",
    }
    result = {}
    for key, value in row.items():
        result[key] = int(value) if key in integer_fields else _finite(value, key)
    total = result["total_cells"]
    viable = result["viable_cells"]
    result.update(
        {
            "viable_fraction": viable / total if total else 0.0,
            "apoptotic_fraction": result["apoptotic_cells"] / total if total else 0.0,
            "necrotic_fraction": result["necrotic_cells"] / total if total else 0.0,
            "resistant_viable_fraction": (
                result["resistant_viable_cells"] / viable if viable else 0.0
            ),
            "hypoxic_viable_fraction": (result["hypoxic_viable_cells"] / viable if viable else 0.0),
        }
    )
    return result


def _cells(path):
    fields = {
        "x_um": float,
        "y_um": float,
        "z_um": float,
        "dead": int,
        "apoptotic": int,
        "necrotic": int,
        "resistant": int,
        "oxygen_mmhg": float,
        "therapeutic": float,
        "damage": float,
    }
    columns = {name: [] for name in fields}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            for name, parser in fields.items():
                value = parser(row[name])
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"PhysiCell returned a non-finite cell field: {name}")
                columns[name].append(value)
    return columns


def run_assay(*, seed, protocol, patient, settings):
    executable = _executable()
    with tempfile.TemporaryDirectory(prefix="synthetic-lab-organoid-") as directory:
        work = Path(directory)
        output = work / "output"
        output.mkdir()
        config = _write_config(_base_config(executable), output, seed, protocol, patient, settings)
        completed = subprocess.run(
            [str(executable), str(config)],
            cwd=work,
            text=True,
            capture_output=True,
            timeout=settings["solver_timeout_s"],
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout)[-4000:]
            raise RuntimeError(f"PhysiCell organoid assay failed: {message}")
        summary_path = output / "summary.csv"
        cells_path = output / "cells.csv"
        if not summary_path.is_file() or not cells_path.is_file():
            raise RuntimeError("PhysiCell completed without summary.csv and cells.csv")
        return {
            "summary": _summary(summary_path),
            "cells": _cells(cells_path),
            "solver_stdout_tail": completed.stdout[-2000:],
        }
