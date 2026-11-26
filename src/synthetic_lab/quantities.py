"""Small, explicit SI conversions at the instrument boundary."""

import math

UNITS = {
    "s": ("time", 1.0, 0.0),
    "ms": ("time", 1e-3, 0.0),
    "us": ("time", 1e-6, 0.0),
    "min": ("time", 60.0, 0.0),
    "W": ("power", 1.0, 0.0),
    "mW": ("power", 1e-3, 0.0),
    "uW": ("power", 1e-6, 0.0),
    "V": ("voltage", 1.0, 0.0),
    "mV": ("voltage", 1e-3, 0.0),
    "A": ("current", 1.0, 0.0),
    "mA": ("current", 1e-3, 0.0),
    "rad": ("angle", 1.0, 0.0),
    "mrad": ("angle", 1e-3, 0.0),
    "deg": ("angle", math.pi / 180.0, 0.0),
    "K": ("temperature", 1.0, 0.0),
    "degC": ("temperature", 1.0, 273.15),
    "K/W": ("thermal_resistance", 1.0, 0.0),
    "J/K": ("heat_capacity", 1.0, 0.0),
    "ohm": ("resistance", 1.0, 0.0),
    "Ah": ("charge", 3600.0, 0.0),
    "C": ("charge", 1.0, 0.0),
    "m": ("length", 1.0, 0.0),
    "mm": ("length", 1e-3, 0.0),
    "um": ("length", 1e-6, 0.0),
    "nm": ("length", 1e-9, 0.0),
    "m/s": ("velocity", 1.0, 0.0),
    "um/s": ("velocity", 1e-6, 0.0),
    "nm/s": ("velocity", 1e-9, 0.0),
    "L": ("volume", 1.0, 0.0),
    "mL": ("volume", 1e-3, 0.0),
    "m3": ("volume", 1000.0, 0.0),
    "mol/L": ("concentration", 1.0, 0.0),
    "mmol/L": ("concentration", 1e-3, 0.0),
    "J/mol": ("molar_energy", 1.0, 0.0),
    "kJ/mol": ("molar_energy", 1e3, 0.0),
    "W/K": ("thermal_conductance", 1.0, 0.0),
    "1/s": ("rate", 1.0, 0.0),
}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Expected a finite number")
    return result


def quantity(value, unit=None):
    if not isinstance(value, dict):
        return number(value)
    if set(value) != {"value", "unit"}:
        raise ValueError("A quantity requires exactly value and unit")
    source = value["unit"]
    if isinstance(source, str) and unit is not None and source == unit:
        return number(value["value"])
    if not isinstance(source, str) or source not in UNITS or unit not in UNITS:
        raise ValueError(f"Unsupported conversion from {source!r} to {unit!r}")
    source_dim, source_scale, source_offset = UNITS[source]
    target_dim, target_scale, target_offset = UNITS[unit]
    if source_dim != target_dim:
        raise ValueError(f"Incompatible dimensions: {source} and {unit}")
    return (number(value["value"]) * source_scale + source_offset - target_offset) / target_scale
