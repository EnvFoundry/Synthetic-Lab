import os

import pytest

from synthetic_lab import Lab, Worker

pytest.importorskip("physicell_car_t")

if not os.environ.get("PHYSICELL_CART_EXECUTABLE"):
    pytest.skip(
        "PhysiCell CAR-T spheroid executable is not configured",
        allow_module_level=True,
    )


FAST_CONFIG = {
    "tumor_radius_um": 42.0,
    "antigen_mean": 1.0,
    "antigen_sd": 0.25,
    "antigen_negative_fraction": 0.15,
    "patient_variation": 0.0,
    "diffusion_dt_min": 0.10,
    "omp_threads": 2,
    "solver_timeout_s": 240.0,
}

PROTOCOL = {
    "pre_growth_hours": 0.0,
    "treatment_hours": 8.0,
    "attachment_rate_per_min": 0.20,
    "dwell_time_min": 20.0,
    "kill_rate_per_min": 0.10,
    "motility_speed_um_min": 1.0,
}


def test_car_t_laboratory_is_discovered_with_solver_contract():
    descriptions = {item["name"]: item for item in Lab.catalogue()}
    description = descriptions["physicell-car-t-spheroid"]
    contract = description["research_contract"]
    assert contract["metadata"]["solver_backend"].startswith("PhysiCell 1.14.2")
    assert contract["metadata"]["upstream_model"] == "cancer-immune-sample"
    assert contract["validity"]["fidelity"] == "hybrid"
    assert set(contract["action_semantics"]) == set(description["actions"])


def test_car_t_changes_the_same_seeded_spheroid_and_reports_functional_state():
    with Lab(":memory:") as lab:
        root = lab.create("physicell-car-t-spheroid", seed=41, config=FAST_CONFIG)
        untreated = root.fork()
        treated = root.fork()
        baseline = untreated.act("infuse", car_t_cells=0, **PROTOCOL)["observations"]
        response = treated.act("infuse", car_t_cells=120, **PROTOCOL)["observations"]

        assert baseline["tumor_total_cells"]["value"] > 0
        assert response["tumor_total_cells"]["value"] > 0
        assert response["car_t_cells"]["value"] > 0
        assert 0.0 <= response["mean_exhaustion"]["value"] <= 1.0
        assert 0.0 <= response["infiltrating_fraction"]["value"] <= 1.0
        assert response["total_contacts"]["value"] >= response["total_kills"]["value"]
        assert response["tumor_viable_fraction"]["value"] <= (
            baseline["tumor_viable_fraction"]["value"] + 1e-12
        )


def test_dwell_time_is_a_real_intervention_not_hidden_metadata():
    with Lab(":memory:") as lab:
        root = lab.create("physicell-car-t-spheroid", seed=53, config=FAST_CONFIG)
        fast = root.fork().act("infuse", car_t_cells=100, **dict(PROTOCOL, dwell_time_min=4.0))[
            "observations"
        ]
        slow = root.fork().act("infuse", car_t_cells=100, **dict(PROTOCOL, dwell_time_min=90.0))[
            "observations"
        ]

        changed = (
            fast["total_contacts"]["value"] != slow["total_contacts"]["value"]
            or fast["mean_exhaustion"]["value"] != slow["mean_exhaustion"]["value"]
            or fast["infiltrating_fraction"]["value"] != slow["infiltrating_fraction"]["value"]
        )
        assert changed


def test_worker_executes_car_t_assay_and_cell_map_uses_external_storage(tmp_path):
    database = tmp_path / "car-t.sqlite"
    with Lab(database, artifact_threshold=512) as lab:
        assay = lab.create("physicell-car-t-spheroid", seed=17, config=FAST_CONFIG)
        assay.submit(
            "infuse",
            car_t_cells=100,
            operation_id="car-t-treatment",
            **PROTOCOL,
        )
        identifier = assay.id

    with Lab(database, artifact_threshold=512) as lab:
        result = Worker(
            lab,
            models=("physicell-car-t-spheroid",),
            worker_id="car-t-worker",
        ).run_once()
        assert result["status"] == "succeeded"

    with Lab(database, artifact_threshold=512) as lab:
        assay = lab.session(identifier)
        snapshot = assay.act("snapshot")["observations"]["cell_map"]
        assert "$artifact" in snapshot["value"]
        restored = lab.read_artifact(snapshot["value"]["$artifact"]["id"])
        assert len(restored["x_um"]) == snapshot["shape"][0]
        assert len(restored["exhaustion"]) == snapshot["shape"][0]
        assert {0, 1}.issubset(set(restored["cell_type"]))
        with pytest.raises(ValueError, match="already received"):
            assay.act("infuse", car_t_cells=10, **PROTOCOL)
