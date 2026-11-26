import math
import random
from copy import deepcopy

import pytest
from optical_metrology.microscopy import FluorescenceMicroscopy
from optical_metrology.thin_film import WAVELENGTHS_NM, ThinFilmBench


def sharpness(image):
    total = 0.0
    for row in range(1, len(image) - 1):
        for column in range(1, len(image[row]) - 1):
            laplacian = (
                4 * image[row][column]
                - image[row - 1][column]
                - image[row + 1][column]
                - image[row][column - 1]
                - image[row][column + 1]
            )
            total += laplacian * laplacian
    return total


def test_zero_thickness_is_air_substrate_interface():
    model = ThinFilmBench({"variation": 0})
    state = model.initial(random.Random(1))
    expected = ((1.0 - 1.52) / (1.0 + 1.52)) ** 2
    for wavelength in WAVELENGTHS_NM:
        assert model.reflectance(state, wavelength) == pytest.approx(expected, abs=1e-12)


def test_opaque_absorbing_film_approaches_its_front_surface():
    model = ThinFilmBench({"variation": 0, "extinction": 0.5, "base_roughness": 0})
    state = model.initial(random.Random(1))
    index = complex(model.effective_index(state), 0.5)
    expected = abs((1 - index) / (1 + index)) ** 2
    for thickness in (10_000, 1_000_000):
        state["thickness_nm"] = thickness
        assert model.reflectance(state, 550) == pytest.approx(expected, abs=1e-12)


def test_annealing_conserves_solid_material_while_film_shrinks():
    model = ThinFilmBench({"variation": 0})
    state = model.initial(random.Random(1))
    state.update(thickness_nm=100, temperature_k=700, temperature_setpoint_k=700)
    solid = state["thickness_nm"] * (1 - state["porosity"])
    model.advance(state, 1800)
    assert state["thickness_nm"] < 100
    assert state["thickness_nm"] * (1 - state["porosity"]) == pytest.approx(solid)


def test_porosity_bounds_describe_densification():
    with pytest.raises(ValueError, match="porosity"):
        ThinFilmBench({"deposition_porosity": 0.1, "residual_porosity": 0.2})


def test_deposition_shutter_and_anneal_change_optical_state():
    model = ThinFilmBench({"variation": 0})
    state = model.initial(random.Random(2))
    state.update(rate_command_nm_s=1.0, shutter="open")
    model.advance(state, 100.0)
    assert state["thickness_nm"] == pytest.approx(100.0)
    before = [model.reflectance(state, wavelength) for wavelength in WAVELENGTHS_NM]
    state["shutter"] = "closed"
    model.advance(state, 100.0)
    assert state["thickness_nm"] == pytest.approx(100.0)
    porosity = state["porosity"]
    roughness = state["roughness_nm"]
    state["temperature_setpoint_k"] = 700.0
    model.advance(state, 1800.0)
    after = [model.reflectance(state, wavelength) for wavelength in WAVELENGTHS_NM]
    assert state["porosity"] < porosity
    assert state["roughness_nm"] < roughness
    assert after != pytest.approx(before)
    assert all(0.0 <= value <= 1.0 for value in after)


def test_thin_film_evolution_is_partition_independent_at_one_second_resolution():
    model = ThinFilmBench({"variation": 0})
    whole = model.initial(random.Random(8))
    divided = model.initial(random.Random(8))
    for state in (whole, divided):
        state.update(
            rate_command_nm_s=0.7,
            shutter="open",
            temperature_setpoint_k=650.0,
        )
    model.advance(whole, 300.0)
    for _ in range(300):
        model.advance(divided, 1.0)
    for key in ("thickness_nm", "porosity", "roughness_nm", "temperature_k"):
        assert whole[key] == pytest.approx(divided[key], abs=1e-12)


def test_interferometric_phase_is_periodic_but_spectrum_is_not_identical():
    model = ThinFilmBench({"variation": 0})
    first = model.initial(random.Random(3))
    second = model.initial(random.Random(3))
    index = model.effective_index(first)
    period = 632.8 / (2.0 * index)
    first["thickness_nm"] = 120.0
    second["thickness_nm"] = 120.0 + period
    phase_a = 4.0 * math.pi * index * first["thickness_nm"] / 632.8
    phase_b = 4.0 * math.pi * index * second["thickness_nm"] / 632.8
    cycles = (phase_b - phase_a) / (2.0 * math.pi)
    assert cycles == pytest.approx(round(cycles), abs=1e-12)
    spectrum_a = [model.reflectance(first, wavelength) for wavelength in WAVELENGTHS_NM]
    spectrum_b = [model.reflectance(second, wavelength) for wavelength in WAVELENGTHS_NM]
    assert spectrum_a != pytest.approx(spectrum_b)


def test_focus_controls_image_sharpness_and_counts_stay_in_range():
    model = FluorescenceMicroscopy({"variation": 0})
    focused = model.initial(random.Random(5))
    defocused = model.initial(random.Random(5))
    focused["focus_z_um"] = focused["true_focus_um"]
    defocused["focus_z_um"] = focused["true_focus_um"] + 2.0
    focused["exposure_s"] = 0.08
    defocused["exposure_s"] = 0.08
    focused_image = model.perform(focused, random.Random(11), "read", {"instrument": "camera"})[
        "image"
    ]["value"]
    defocused_image = model.perform(defocused, random.Random(11), "read", {"instrument": "camera"})[
        "image"
    ]["value"]
    assert sharpness(focused_image) > sharpness(defocused_image)
    maximum = int(model.config["camera_max"])
    assert min(map(min, focused_image)) >= 0
    assert max(map(max, focused_image)) <= maximum


def test_photon_dose_irreversibly_reduces_later_fluorescence():
    model = FluorescenceMicroscopy({"variation": 0, "bleach": 0.2})
    low_dose = model.initial(random.Random(7))
    high_dose = model.initial(random.Random(7))
    high_dose.update(illumination_mw=5.0, exposure_s=1.0)
    model.perform(high_dose, random.Random(3), "read", {"instrument": "camera"})
    low_dose.update(illumination_mw=0.1)
    high_dose.update(illumination_mw=0.1)
    remaining_low = model.perform(low_dose, random.Random(9), "read", {"instrument": "photometer"})[
        "total_fluorescence"
    ]["value"]
    remaining_high = model.perform(
        high_dose, random.Random(9), "read", {"instrument": "photometer"}
    )["total_fluorescence"]["value"]
    assert remaining_high < remaining_low
    assert all(0.0 <= emitter["remaining"] <= 1.0 for emitter in high_dose["emitters"])


def test_drift_moves_image_centroid_with_fixed_stage():
    model = FluorescenceMicroscopy({"variation": 0, "drift": 0.01})
    state = model.initial(random.Random(10))
    before_x = state["drift_x_um"]
    before_y = state["drift_y_um"]
    model.advance(state, 100.0)
    displacement = math.hypot(
        state["drift_x_um"] - before_x,
        state["drift_y_um"] - before_y,
    )
    assert displacement == pytest.approx(1.0)


def test_subpixel_motion_preserves_collected_photons_inside_field():
    model = FluorescenceMicroscopy({"variation": 0, "bleach": 0, "drift": 0})
    state = model.initial(random.Random(1))
    state["focus_z_um"] = state["true_focus_um"]
    emitter = dict(state["emitters"][0], x_um=0, y_um=0)
    state["emitters"] = [emitter]
    photons = state["illumination_mw"] * state["exposure_s"] * emitter["green"] * state["gain"]
    for offset in (0, 0.1, 0.175, 0.3):
        state["stage_x_um"] = offset
        image = model._expected_image(state, background=False)
        assert sum(map(sum, image)) == pytest.approx(photons, rel=1e-12)


def test_photometer_uses_camera_field_and_exposure_integrates_bleaching():
    model = FluorescenceMicroscopy({"variation": 0, "bleach": 2, "drift": 0, "read_noise": 0})
    state = model.initial(random.Random(1))
    state.update(illumination_mw=5, exposure_s=1)
    start = deepcopy(state)
    whole = model._expected_image(state, background=False)
    split = model._expected_image(state, duration=0.5, background=False)
    model._bleach(state, 2.5)
    second = model._expected_image(state, duration=0.5, background=False)
    assert sum(map(sum, whole)) == pytest.approx(sum(map(sum, split)) + sum(map(sum, second)))
    start["stage_x_um"] = 20
    start["stage_y_um"] = 20
    assert sum(map(sum, model._expected_image(start, background=False))) == 0
    result = model.perform(start, random.Random(1), "read", {"instrument": "photometer"})
    assert result["total_fluorescence"]["value"] == 0


@pytest.mark.parametrize("key,value", [("pixels", 32.5), ("camera_max", 65535.5)])
def test_camera_dimensions_and_counts_are_integral(key, value):
    with pytest.raises(ValueError, match="integer"):
        FluorescenceMicroscopy({key: value})


def test_domain_package_is_discovered_with_complete_research_contracts():
    from synthetic_lab import Lab

    catalogue = {description["name"]: description for description in Lab.catalogue()}
    for name in ("thin-film", "fluorescence-microscopy"):
        description = catalogue[name]
        contract = description["research_contract"]
        assert set(contract["action_semantics"]) == set(description["actions"])
        assert contract["questions"]
        assert contract["observables"]
        assert contract["validity"]["conditions"]
        assert contract["validity"]["limitations"]
