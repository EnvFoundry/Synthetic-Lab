import os

import pytest

from synthetic_lab import Lab, Worker

pytest.importorskip("physicell_organoid")

if not os.environ.get("PHYSICELL_ORGANOID_EXECUTABLE"):
    pytest.skip("PhysiCell organoid executable is not configured", allow_module_level=True)


FAST_CONFIG = {
    "tumor_radius_um": 45.0,
    "resistant_fraction_mean": 0.20,
    "resistant_fraction_sd": 0.0,
    "patient_variation": 0.0,
    "diffusion_dt_min": 0.08,
    "omp_threads": 1,
    "solver_timeout_s": 180.0,
}

PROTOCOL = {
    "pre_culture_hours": 0.0,
    "exposure_hours": 8.0,
    "recovery_hours": 0.0,
}


def test_organoid_laboratory_is_discovered_with_solver_contract():
    descriptions = {item["name"]: item for item in Lab.catalogue()}
    description = descriptions["physicell-tumor-organoid"]
    contract = description["research_contract"]
    assert contract["metadata"]["solver_backend"].startswith("PhysiCell 1.14.2")
    assert contract["validity"]["fidelity"] == "hybrid"
    assert set(contract["action_semantics"]) == set(description["actions"])


def test_treatment_changes_the_same_seeded_organoid_response():
    with Lab(":memory:") as lab:
        root = lab.create("physicell-tumor-organoid", seed=31, config=FAST_CONFIG)
        untreated = root.fork()
        treated = root.fork()
        baseline = untreated.act("expose", concentration=0.0, **PROTOCOL)["observations"]
        response = treated.act("expose", concentration=2.0, **PROTOCOL)["observations"]
        assert baseline["total_cells"]["value"] > 0
        assert response["total_cells"]["value"] > 0
        assert response["mean_damage"]["value"] > baseline["mean_damage"]["value"]
        assert response["viable_cells"]["value"] < baseline["viable_cells"]["value"]


def test_resistant_labels_survive_equal_repair_rates_and_matched_forks():
    with Lab(":memory:", artifact_threshold=None) as lab:
        root = lab.create(
            "physicell-tumor-organoid",
            seed=17,
            config={
                **FAST_CONFIG,
                "sensitive_repair_rate": 0,
                "resistant_repair_ratio": 1,
                "resistant_fraction_mean": 0.5,
            },
        )
        maps = []
        for _ in range(2):
            assay = root.fork()
            result = assay.act(
                "expose",
                concentration=0,
                pre_culture_hours=0.001,
                exposure_hours=1.001,
                recovery_hours=0.003,
            )
            assert result["end_s"] == pytest.approx(1.005 * 3600)
            cells = assay.act("snapshot")["observations"]["cell_map"]["value"]
            assert set(cells["resistant"]) == {0, 1}
            viable_resistant = sum(
                r and not d for r, d in zip(cells["resistant"], cells["dead"], strict=True)
            )
            assert result["observations"]["resistant_viable_cells"]["value"] == viable_resistant
            maps.append(cells)
        assert maps[0] == maps[1]


def test_worker_executes_assay_and_cell_map_uses_external_storage(tmp_path):
    database = tmp_path / "organoid.sqlite"
    with Lab(database, artifact_threshold=512) as lab:
        assay = lab.create("physicell-tumor-organoid", seed=7, config=FAST_CONFIG)
        assay.submit(
            "expose",
            concentration=1.2,
            operation_id="treatment",
            **PROTOCOL,
        )
        identifier = assay.id

    with Lab(database, artifact_threshold=512) as lab:
        result = Worker(
            lab,
            models=("physicell-tumor-organoid",),
            worker_id="physicell-worker",
        ).run_once()
        assert result["status"] == "succeeded"

    with Lab(database, artifact_threshold=512) as lab:
        assay = lab.session(identifier)
        snapshot = assay.act("snapshot")["observations"]["cell_map"]
        assert "$artifact" in snapshot["value"]
        restored = lab.read_artifact(snapshot["value"]["$artifact"]["id"])
        assert len(restored["x_um"]) == snapshot["shape"][0]
        assert len(restored["damage"]) == snapshot["shape"][0]
        with pytest.raises(ValueError, match="already been exposed"):
            assay.act("expose", concentration=0.5, **PROTOCOL)
