"""Meep simulations used by the photonic-cavity laboratory."""

from __future__ import annotations

import math

import meep as mp
import numpy as np


def _finite(values, name):
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"Meep returned an empty or non-finite {name}")
    return array


def _cell_parameters(defect_spacing, holes_per_side, resolution):
    padding = 2.0
    pml = 1.0
    requested_sx = 2.0 * (padding + pml + holes_per_side) + defect_spacing - 1.0
    sx = math.ceil(requested_sx * resolution - 1e-12) / resolution
    sy = math.ceil(6.0 * resolution - 1e-12) / resolution
    return sx, sy, pml


def _geometry(hole_radius, defect_spacing, holes_per_side, epsilon, waveguide_width):
    geometry = [
        mp.Block(
            size=mp.Vector3(mp.inf, waveguide_width, mp.inf),
            material=mp.Medium(epsilon=epsilon),
        )
    ]
    for index in range(holes_per_side):
        offset = defect_spacing / 2.0 + index
        geometry.append(mp.Cylinder(hole_radius, center=mp.Vector3(offset)))
        geometry.append(mp.Cylinder(hole_radius, center=mp.Vector3(-offset)))
    return geometry


def _flux_run(
    *,
    hole_radius,
    defect_spacing,
    holes_per_side,
    epsilon,
    waveguide_width,
    center_frequency,
    frequency_width,
    frequency_points,
    resolution,
    decay_time,
    with_holes,
):
    sx, sy, pml = _cell_parameters(defect_spacing, holes_per_side, resolution)
    source_x = -0.5 * sx + pml
    monitor_x = 0.5 * sx - pml - 0.5
    geometry = [
        mp.Block(
            size=mp.Vector3(mp.inf, waveguide_width, mp.inf),
            material=mp.Medium(epsilon=epsilon),
        )
    ]
    if with_holes:
        geometry = _geometry(
            hole_radius,
            defect_spacing,
            holes_per_side,
            epsilon,
            waveguide_width,
        )

    simulation = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        geometry=geometry,
        sources=[
            mp.Source(
                mp.GaussianSource(center_frequency, fwidth=frequency_width),
                component=mp.Ey,
                center=mp.Vector3(source_x),
                size=mp.Vector3(0, waveguide_width),
            )
        ],
        boundary_layers=[mp.PML(pml)],
        symmetries=[mp.Mirror(mp.Y, phase=-1)],
        resolution=resolution,
    )
    monitor = simulation.add_flux(
        center_frequency,
        frequency_width,
        frequency_points,
        mp.FluxRegion(
            center=mp.Vector3(monitor_x),
            size=mp.Vector3(0, 2.0 * waveguide_width),
        ),
    )
    simulation.run(until_after_sources=decay_time)
    frequencies = _finite(mp.get_flux_freqs(monitor), "frequency axis")
    flux = _finite(mp.get_fluxes(monitor), "transmitted flux")
    simulation.reset_meep()
    return frequencies, flux


def transmission_spectrum(
    *,
    hole_radius,
    defect_spacing,
    holes_per_side,
    epsilon,
    waveguide_width,
    center_frequency,
    frequency_width,
    frequency_points,
    resolution,
    decay_time,
):
    reference_frequency, reference_flux = _flux_run(
        hole_radius=hole_radius,
        defect_spacing=defect_spacing,
        holes_per_side=holes_per_side,
        epsilon=epsilon,
        waveguide_width=waveguide_width,
        center_frequency=center_frequency,
        frequency_width=frequency_width,
        frequency_points=frequency_points,
        resolution=resolution,
        decay_time=decay_time,
        with_holes=False,
    )
    device_frequency, device_flux = _flux_run(
        hole_radius=hole_radius,
        defect_spacing=defect_spacing,
        holes_per_side=holes_per_side,
        epsilon=epsilon,
        waveguide_width=waveguide_width,
        center_frequency=center_frequency,
        frequency_width=frequency_width,
        frequency_points=frequency_points,
        resolution=resolution,
        decay_time=decay_time,
        with_holes=True,
    )
    if not np.allclose(reference_frequency, device_frequency, rtol=0.0, atol=1e-12):
        raise ValueError("Reference and device runs returned different frequency axes")
    if np.any(np.abs(reference_flux) < 1e-12):
        raise ValueError("Reference waveguide flux is too small for normalization")

    transmission = np.maximum(0.0, device_flux / reference_flux)
    wavelength = 1.0 / device_frequency
    order = np.argsort(wavelength)
    return {
        "frequency_inverse_um": device_frequency[order].tolist(),
        "wavelength_um": wavelength[order].tolist(),
        "transmission": transmission[order].tolist(),
    }


def _quadratic_peak(frequency, transmission, peak_index):
    sampled_frequency = float(frequency[peak_index])
    sampled_transmission = float(transmission[peak_index])
    if peak_index == 0 or peak_index + 1 == transmission.size:
        return sampled_frequency, sampled_transmission, False

    left = float(transmission[peak_index - 1])
    center = sampled_transmission
    right = float(transmission[peak_index + 1])
    curvature = left - 2.0 * center + right
    if curvature >= 0.0 or abs(curvature) < 1e-15:
        return sampled_frequency, sampled_transmission, False

    offset = 0.5 * (left - right) / curvature
    if abs(offset) > 1.0:
        return sampled_frequency, sampled_transmission, False

    frequency_step = float(frequency[peak_index + 1] - frequency[peak_index])
    fitted_frequency = sampled_frequency + offset * frequency_step
    fitted_transmission = center - 0.25 * (left - right) * offset
    if fitted_frequency <= 0.0 or fitted_transmission < center:
        return sampled_frequency, sampled_transmission, False
    return fitted_frequency, fitted_transmission, True


def resonance_summary(spectrum, center_frequency, frequency_width):
    frequency = _finite(spectrum["frequency_inverse_um"], "frequency axis")
    transmission = _finite(spectrum["transmission"], "transmission spectrum")
    central = np.flatnonzero(np.abs(frequency - center_frequency) <= 0.4 * frequency_width)
    if central.size < 5:
        central = np.arange(frequency.size)
    local = transmission[central]
    peak_index = int(central[int(np.argmax(local))])
    fitted_frequency, fitted_peak, interpolated = _quadratic_peak(
        frequency, transmission, peak_index
    )
    floor = float(np.percentile(local, 20.0))
    prominence = fitted_peak - floor
    half_level = floor + 0.5 * max(0.0, prominence)

    left = peak_index
    while left > 0 and transmission[left] >= half_level:
        left -= 1
    right = peak_index
    while right + 1 < transmission.size and transmission[right] >= half_level:
        right += 1

    quality_factor = None
    if left < peak_index < right:
        linewidth = abs(float(frequency[right] - frequency[left]))
        if linewidth > 0.0:
            quality_factor = fitted_frequency / linewidth

    return {
        "resonance_frequency_inverse_um": fitted_frequency,
        "resonance_wavelength_um": 1.0 / fitted_frequency,
        "sampled_resonance_wavelength_um": 1.0 / float(frequency[peak_index]),
        "resonance_interpolated": interpolated,
        "peak_transmission": fitted_peak,
        "spectral_floor": floor,
        "spectral_contrast": prominence,
        "quality_factor": quality_factor,
    }


def resonant_field(
    *,
    hole_radius,
    defect_spacing,
    holes_per_side,
    epsilon,
    waveguide_width,
    frequency,
    resolution,
    run_time,
):
    sx, sy, pml = _cell_parameters(defect_spacing, holes_per_side, resolution)
    source_x = -0.5 * sx + pml
    simulation = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        geometry=_geometry(
            hole_radius,
            defect_spacing,
            holes_per_side,
            epsilon,
            waveguide_width,
        ),
        sources=[
            mp.Source(
                mp.ContinuousSource(frequency=frequency, width=20.0),
                component=mp.Ey,
                center=mp.Vector3(source_x),
                size=mp.Vector3(0, waveguide_width),
            )
        ],
        boundary_layers=[mp.PML(pml)],
        symmetries=[mp.Mirror(mp.Y, phase=-1)],
        resolution=resolution,
        force_complex_fields=True,
    )
    simulation.run(until=run_time)
    field = simulation.get_array(
        center=mp.Vector3(),
        size=mp.Vector3(sx - 2.0 * pml, sy - 2.0 * pml),
        component=mp.Ey,
    )
    intensity = np.abs(field) ** 2
    intensity = _finite(intensity, "field intensity")
    peak = float(np.max(intensity))
    if peak > 0.0:
        intensity = intensity / peak
    simulation.reset_meep()
    return {
        "value": intensity.tolist(),
        "shape": list(intensity.shape),
        "extent_um": [
            -0.5 * (sx - 2.0 * pml),
            0.5 * (sx - 2.0 * pml),
            -0.5 * (sy - 2.0 * pml),
            0.5 * (sy - 2.0 * pml),
        ],
    }
