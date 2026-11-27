import os
import xml.etree.ElementTree as ET
from pathlib import Path

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
    "omp_threads": 1,
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
        assert response["tumor_viable_cells"]["value"] < baseline["tumor_viable_cells"]["value"]


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


def test_worker_executes_car_t_assay_and_cell_map_uses_external_storage(
    tmp_path, assert_protocol_result
):
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
        assert_protocol_result(result["result"])

    with Lab(database, artifact_threshold=512) as lab:
        assay = lab.session(identifier)
        result = assay.act("snapshot")
        assert_protocol_result(result)
        snapshot = result["observations"]["cell_map"]
        assert "$artifact" in snapshot["value"]
        restored = lab.read_artifact(snapshot["value"]["$artifact"]["id"])
        assert len(restored["x_um"]) == snapshot["shape"][0]
        assert len(restored["exhaustion"]) == snapshot["shape"][0]
        assert {0, 1}.issubset(set(restored["cell_type"]))
        with pytest.raises(ValueError, match="already received"):
            assay.act("infuse", car_t_cells=10, **PROTOCOL)


def test_kills_count_distinct_deaths_and_matched_runs_agree(tmp_path, monkeypatch):
    source = Path(
        os.environ.get(
            "PHYSICELL_CART_CONFIG",
            str(
                Path(os.environ["PHYSICELL_CART_EXECUTABLE"]).parent
                / "config/PhysiCell_settings.xml"
            ),
        )
    )
    tree = ET.parse(source)
    # With division disabled, every CAR-triggered death consumes one initial tumor cell.
    rates = tree.findall(
        './cell_definitions/cell_definition[@name="cancer cell"]/phenotype/cycle/'
        "phase_transition_rates/rate"
    )
    assert rates
    for rate in rates:
        rate.text = "0"
    config = tmp_path / "nondividing.xml"
    tree.write(config)
    monkeypatch.setenv("PHYSICELL_CART_CONFIG", str(config))
    protocol = dict(
        PROTOCOL,
        treatment_hours=2.001,
        pre_growth_hours=0.003,
        attachment_rate_per_min=2,
        kill_rate_per_min=2,
    )
    with Lab(":memory:", artifact_threshold=None) as lab:
        root = lab.create(
            "physicell-car-t-spheroid",
            seed=7,
            config={
                **FAST_CONFIG,
                "antigen_mean": 1.5,
                "antigen_sd": 0,
                "antigen_negative_fraction": 0,
                "antigen_loss_rate_per_min": 0,
            },
        )
        control = root.fork().act("infuse", car_t_cells=0, **protocol)["observations"]
        maps = []
        counts = []
        for _ in range(2):
            assay = root.fork()
            result = assay.act("infuse", car_t_cells=200, **protocol)
            assert result["end_s"] == pytest.approx(2.004 * 3600)
            observations = result["observations"]
            kills = observations["total_kills"]["value"]
            assert 0 < kills <= control["tumor_total_cells"]["value"]
            assert (
                kills + observations["tumor_viable_cells"]["value"]
                <= (control["tumor_total_cells"]["value"])
            )
            cells = assay.act("snapshot")["observations"]["cell_map"]["value"]
            radius = observations["infusion_radius"]["value"]
            immune_radii = [
                (x * x + y * y + z * z) ** 0.5
                for kind, x, y, z in zip(
                    cells["cell_type"], cells["x_um"], cells["y_um"], cells["z_um"], strict=True
                )
                if kind == 1
            ]
            assert observations["infiltrating_fraction"]["value"] == pytest.approx(
                sum(r <= radius for r in immune_radii) / len(immune_radii)
            )
            maps.append(cells)
            counts.append(kills)
        assert maps[0] == maps[1]
        assert counts[0] == counts[1]


def test_antigen_negative_population_has_no_car_mediated_killing():
    with Lab(":memory:") as lab:
        assay = lab.create(
            "physicell-car-t-spheroid",
            seed=9,
            config={
                **FAST_CONFIG,
                "antigen_mean": 0,
                "antigen_sd": 0,
            },
        )
        result = assay.act("infuse", car_t_cells=80, **dict(PROTOCOL, treatment_hours=1))[
            "observations"
        ]
        assert result["total_contacts"]["value"] == 0
        assert result["total_kills"]["value"] == 0
        assert result["antigen_low_viable_fraction"]["value"] == 1


def test_empty_endpoint_is_a_valid_assay_result(tmp_path):
    from physicell_car_t.solver import _cells, _summary

    fields = [
        "tumor_total_cells",
        "tumor_viable_cells",
        "tumor_apoptotic_cells",
        "tumor_necrotic_cells",
        "antigen_low_viable_cells",
        "immune_cells",
        "infiltrating_immune_cells",
        "exhausted_immune_cells",
        "engaged_immune_cells",
    ]
    summary = tmp_path / "summary.csv"
    summary.write_text(",".join(fields) + "\n" + ",".join("0" for _ in fields) + "\n")
    assert _summary(summary)["tumor_viable_fraction"] == 0
    cells = tmp_path / "cells.csv"
    cells.write_text(
        "cell_type,x_um,y_um,z_um,dead,apoptotic,necrotic,car_antigen,"
        "oxygen_mmhg,exhaustion,engaged,contact_events,kills\n"
    )
    assert all(column == [] for column in _cells(cells).values())
