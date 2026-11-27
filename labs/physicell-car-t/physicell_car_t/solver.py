"""Run and read the external PhysiCell CAR-T spheroid project."""

from __future__ import annotations

import csv
import math
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

_EXECUTABLE_ENV = "PHYSICELL_CART_EXECUTABLE"
_CONFIG_ENV = "PHYSICELL_CART_CONFIG"


def _finite(value, name):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"PhysiCell returned a non-finite {name}")
    return result


def _executable():
    raw = os.environ.get(_EXECUTABLE_ENV)
    if not raw:
        raise FileNotFoundError(f"Set {_EXECUTABLE_ENV} to the compiled car_t_spheroid executable")
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
        raise FileNotFoundError(f"PhysiCell CAR-T configuration does not exist: {path}")
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


def _cell_definition(root, name):
    for node in root.findall("./cell_definitions/cell_definition"):
        if node.get("name") == name:
            return node
    raise ValueError(f"Missing PhysiCell cell definition: {name}")


def _custom(cell, name, value, units="dimensionless"):
    parent = cell.find("./custom_data")
    if parent is None:
        parent = ET.SubElement(cell, "custom_data")
    node = parent.find(name)
    if node is None:
        node = ET.SubElement(parent, name, {"units": units})
    node.text = str(value)


def _write_config(path, output, seed, protocol, patient, settings):
    tree = ET.parse(path)
    root = tree.getroot()

    pre_growth_min = 60.0 * protocol["pre_growth_hours"]
    total_minutes = pre_growth_min + 60.0 * protocol["treatment_hours"]
    half_width = max(180.0, settings["tumor_radius_um"] + 120.0)

    for axis in ("x", "y", "z"):
        _set(root, f"./domain/{axis}_min", -half_width)
        _set(root, f"./domain/{axis}_max", half_width)
    _set(root, "./domain/use_2D", "false")
    _set(root, "./overall/max_time", total_minutes)
    _set(root, "./overall/dt_diffusion", settings["diffusion_dt_min"])
    _set(root, "./parallel/omp_num_threads", settings["omp_threads"])
    _set(root, "./save/folder", output.as_posix())
    _set(root, "./save/full_data/enable", "false")
    _set(root, "./save/SVG/enable", "false")
    _set(root, "./options/virtual_wall_at_domain_edge", "true")

    _user_parameter(root, "random_seed", seed, kind="int")
    _user_parameter(root, "immune_activation_time", pre_growth_min, units="min")
    _user_parameter(root, "save_interval_after_therapy_start", total_minutes + 1.0)
    _user_parameter(root, "SVG_interval_after_therapy_start", total_minutes + 1.0)
    _user_parameter(root, "number_of_immune_cells", protocol["car_t_cells"], kind="int")
    _user_parameter(root, "initial_min_immune_distance_from_tumor", 12.0, units="um")
    _user_parameter(root, "thickness_of_immune_seeding_region", 35.0, units="um")
    _user_parameter(root, "tumor_radius", settings["tumor_radius_um"], units="um")
    _user_parameter(root, "tumor_mean_immunogenicity", 1.0)
    _user_parameter(root, "tumor_immunogenicity_standard_deviation", 0.0)

    _user_parameter(root, "tumor_mean_antigen", patient["antigen_mean"])
    _user_parameter(root, "tumor_antigen_sd", patient["antigen_sd"])
    _user_parameter(root, "antigen_negative_fraction", patient["antigen_negative_fraction"])
    _user_parameter(root, "antigen_loss_rate", patient["antigen_loss_rate_per_min"], units="1/min")
    _user_parameter(root, "antigen_threshold", settings["antigen_threshold"])
    _user_parameter(root, "antigen_saturation", settings["antigen_saturation"])
    _user_parameter(
        root,
        "exhaustion_contact_rate",
        settings["exhaustion_contact_rate_per_min"] * patient["exhaustion_scale"],
        units="1/min",
    )
    _user_parameter(
        root,
        "exhaustion_hypoxia_rate",
        settings["exhaustion_hypoxia_rate_per_min"] * patient["exhaustion_scale"],
        units="1/min",
    )
    _user_parameter(
        root,
        "exhaustion_recovery_rate",
        settings["exhaustion_recovery_rate_per_min"],
        units="1/min",
    )
    _user_parameter(root, "kill_exhaustion_floor", settings["kill_exhaustion_floor"])
    _user_parameter(root, "motility_exhaustion_floor", settings["motility_exhaustion_floor"])
    _user_parameter(root, "hypoxia_threshold", settings["hypoxia_threshold_mmhg"], units="mmHg")
    _user_parameter(root, "immune_base_speed", protocol["motility_speed_um_min"], units="um/min")

    tumor = _cell_definition(root, "cancer cell")
    immune = _cell_definition(root, "immune cell")
    _custom(tumor, "car_antigen", 1.0)
    _custom(immune, "car_antigen", 0.0)
    _custom(immune, "car_antigen_threshold", settings["antigen_threshold"])
    _custom(immune, "car_antigen_saturation", settings["antigen_saturation"])
    _custom(immune, "attachment_rate", protocol["attachment_rate_per_min"], "1/min")
    _custom(immune, "attachment_lifetime", protocol["dwell_time_min"], "min")
    _custom(immune, "kill_rate", protocol["kill_rate_per_min"], "1/min")
    _custom(immune, "exhaustion", 0.0)
    _custom(immune, "contact_minutes", 0.0, "min")
    _custom(immune, "contact_events", 0.0, "count")
    _custom(immune, "kills", 0.0, "count")

    _required(immune, "./phenotype/motility/speed").text = str(protocol["motility_speed_um_min"])

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
        "tumor_total_cells",
        "tumor_viable_cells",
        "tumor_apoptotic_cells",
        "tumor_necrotic_cells",
        "antigen_low_viable_cells",
        "immune_cells",
        "infiltrating_immune_cells",
        "exhausted_immune_cells",
        "engaged_immune_cells",
        "total_contacts",
        "total_kills",
    }
    result = {}
    for key, value in row.items():
        result[key] = int(round(float(value))) if key in integer_fields else _finite(value, key)

    tumor_total = result["tumor_total_cells"]
    viable = result["tumor_viable_cells"]
    immune = result["immune_cells"]
    result.update(
        {
            "tumor_viable_fraction": viable / tumor_total if tumor_total else 0.0,
            "tumor_apoptotic_fraction": (
                result["tumor_apoptotic_cells"] / tumor_total if tumor_total else 0.0
            ),
            "tumor_necrotic_fraction": (
                result["tumor_necrotic_cells"] / tumor_total if tumor_total else 0.0
            ),
            "antigen_low_viable_fraction": (
                result["antigen_low_viable_cells"] / viable if viable else 0.0
            ),
            "infiltrating_fraction": (
                result["infiltrating_immune_cells"] / immune if immune else 0.0
            ),
            "exhausted_fraction": (result["exhausted_immune_cells"] / immune if immune else 0.0),
            "engaged_fraction": (result["engaged_immune_cells"] / immune if immune else 0.0),
        }
    )
    return result


def _cells(path):
    fields = {
        "cell_type": int,
        "x_um": float,
        "y_um": float,
        "z_um": float,
        "dead": int,
        "apoptotic": int,
        "necrotic": int,
        "car_antigen": float,
        "oxygen_mmhg": float,
        "exhaustion": float,
        "engaged": int,
        "contact_events": float,
        "kills": float,
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
    with tempfile.TemporaryDirectory(prefix="synthetic-lab-car-t-") as directory:
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
            raise RuntimeError(
                f"PhysiCell CAR-T spheroid assay failed with exit code "
                f"{completed.returncode}: {message}"
            )
        summary_path = output / "summary.csv"
        cells_path = output / "cells.csv"
        if not summary_path.is_file() or not cells_path.is_file():
            raise RuntimeError("PhysiCell completed without summary.csv and cells.csv")
        return {
            "summary": _summary(summary_path),
            "cells": _cells(cells_path),
            "solver_stdout_tail": completed.stdout[-2000:],
        }
