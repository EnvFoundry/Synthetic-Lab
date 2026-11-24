"""Fit a steady-state thermal model from observable readings."""

from .quantities import quantity


def fit_thermal(records):
    """Least squares with an intercept, using settled V, I, sample and ambient T.

    The residual is fit error, not measurement uncertainty. Choose independent
    held-out powers to test the result before using it for a scientific claim.
    """
    powers, rises, references, sources = [], [], [], set()
    for record in records:
        observations = record.get("observations", {})
        if not {"temperature", "ambient", "voltage", "current"} <= observations.keys():
            continue
        values = {}
        for key, unit in (
            ("temperature", "K"),
            ("ambient", "K"),
            ("voltage", "V"),
            ("current", "A"),
        ):
            measurement = observations[key]
            if measurement.get("saturated", False):
                raise ValueError("Saturated readings cannot calibrate a linear thermal model")
            values[key] = quantity(
                {"value": measurement["value"], "unit": measurement["unit"]}, unit
            )
        if record.get("source") not in ("simulation", "measurement"):
            raise ValueError("Each reading must declare simulation or measurement as its source")
        sources.add(record["source"])
        powers.append(values["voltage"] * values["current"])
        rises.append(values["temperature"] - values["ambient"])
        references.append(
            {"session": record.get("session"), "operation_id": record.get("operation_id")}
        )
    if len(sources) > 1:
        raise ValueError("Fit simulated and measured calibration sets separately")
    if len(powers) < 3:
        raise ValueError("At least three settled observations with all four channels are required")
    xmean = sum(powers) / len(powers)
    ymean = sum(rises) / len(rises)
    xx = sum((x - xmean) ** 2 for x in powers)
    if xx < 1e-8:
        raise ValueError("Use distinct heating powers to identify thermal resistance")
    resistance = sum((x - xmean) * (y - ymean) for x, y in zip(powers, rises)) / xx
    offset = ymean - resistance * xmean
    if resistance <= 0:
        raise ValueError("The fitted thermal resistance must be positive")
    residual = (
        sum((y - offset - resistance * x) ** 2 for x, y in zip(powers, rises)) / len(powers)
    ) ** 0.5
    return {
        "model": "steady thermal resistance with thermometer offset",
        "source": sources.pop(),
        "thermal_resistance_k_per_w": resistance,
        "offset_k": offset,
        "fit_rmse_k": residual,
        "power_range_w": [min(powers), max(powers)],
        "observations": len(powers),
        "references": references,
        "assumption": "Readings are at thermal steady state under the same contact and ambient conditions",
    }
