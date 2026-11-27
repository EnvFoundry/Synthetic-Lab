import math

import pytest

from synthetic_lab import Lab, Worker

pytest.importorskip("meep")
solver = pytest.importorskip("meep_photonics.solver")


FAST_CONFIG = {
    "resolution": 7,
    "frequency_points": 15,
    "decay_time": 24,
    "field_run_time": 12,
    "holes_per_side": 1,
    "hole_radius_sigma": 0,
    "defect_spacing_sigma": 0,
    "spectrometer_noise": 0,
    "fabrication_time": 0,
    "spectrum_time": 0,
    "field_time": 0,
}


def test_quadratic_peak_recovers_sub_bin_resonance():
    frequencies = [0.30, 0.28, 0.26, 0.24, 0.22]
    true_frequency = 0.251
    transmission = [1.0 - 100.0 * (value - true_frequency) ** 2 for value in frequencies]
    spectrum = {
        "frequency_inverse_um": frequencies,
        "transmission": transmission,
    }
    summary = solver.resonance_summary(spectrum, center_frequency=0.26, frequency_width=0.10)
    assert summary["resonance_interpolated"]
    assert summary["resonance_frequency_inverse_um"] == pytest.approx(true_frequency, abs=1e-12)
    assert summary["sampled_resonance_wavelength_um"] != pytest.approx(
        summary["resonance_wavelength_um"]
    )


def test_meep_laboratory_is_discovered_with_full_wave_contract():
    descriptions = {item["name"]: item for item in Lab.catalogue()}
    description = descriptions["meep-photonic-cavity"]
    contract = description["research_contract"]
    assert contract["metadata"]["solver_backend"] == "Meep"
    assert contract["validity"]["fidelity"] == "hybrid"
    assert set(contract["action_semantics"]) == set(description["actions"])


def test_broadband_measurement_returns_finite_normalized_spectrum():
    with Lab(":memory:") as lab:
        sample = lab.create("meep-photonic-cavity", seed=3, config=FAST_CONFIG)
        sample.act("fabricate")
        result = sample.act("measure", instrument="summary")
        observations = result["observations"]
        spectrum = observations["transmission_spectrum"]
        resonance = observations["resonance_wavelength"]
        values = spectrum["value"]
        wavelengths = spectrum["axis_values"]
        assert len(values) == FAST_CONFIG["frequency_points"]
        assert len(wavelengths) == len(values)
        assert all(math.isfinite(value) and value >= 0.0 for value in values)
        assert all(math.isfinite(value) and value > 0.0 for value in wavelengths)
        assert resonance["value"] > 0.0
        assert resonance["sampled_wavelength_um"] > 0.0
        assert isinstance(resonance["interpolated"], bool)
        assert sample.status()["configuration"]["solver_runs"] == 2


def test_pre_fabrication_branches_compare_distinct_device_designs():
    with Lab(":memory:") as lab:
        root = lab.create("meep-photonic-cavity", seed=5, config=FAST_CONFIG)
        compact = root.fork()
        open_defect = root.fork()
        compact.act("design", hole_radius=0.34, defect_spacing=1.20)
        open_defect.act("design", hole_radius=0.40, defect_spacing=1.65)
        compact.act("fabricate")
        open_defect.act("fabricate")
        a = compact.act("measure", instrument="spectrum")["observations"]["transmission_spectrum"][
            "value"
        ]
        b = open_defect.act("measure", instrument="spectrum")["observations"][
            "transmission_spectrum"
        ]["value"]
        difference = max(abs(left - right) for left, right in zip(a, b, strict=True))
        assert difference > 1e-4


def test_worker_executes_meep_and_field_map_uses_external_storage(tmp_path):
    database = tmp_path / "photonics.sqlite"
    with Lab(database, artifact_threshold=256) as lab:
        sample = lab.create("meep-photonic-cavity", seed=11, config=FAST_CONFIG)
        sample.act("fabricate")
        sample.submit("measure", instrument="resonance", operation_id="resonance")
        sample.submit("measure", instrument="field", operation_id="field")
        identifier = sample.id

    with Lab(database, artifact_threshold=256) as lab:
        worker = Worker(
            lab,
            models=("meep-photonic-cavity",),
            worker_id="meep-worker",
        )
        assert worker.run_once()["status"] == "succeeded"
        assert worker.run_once()["status"] == "succeeded"

    with Lab(database, artifact_threshold=256) as lab:
        completed = lab.operation(identifier, "field")["result"]
        field = completed["observations"]["field_intensity"]
        assert "$artifact" in field["value"]
        restored = lab.read_artifact(field["value"]["$artifact"]["id"])
        assert len(restored) == field["shape"][0]
        assert len(restored[0]) == field["shape"][1]
        assert max(max(row) for row in restored) == pytest.approx(1.0)
