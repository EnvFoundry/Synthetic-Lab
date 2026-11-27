import importlib.metadata
import math

import pytest

contracts = pytest.importorskip("agent_gym.contracts")
optical_tasks = pytest.importorskip("optical_metrology.agent_gym")
TaskSpec = contracts.TaskSpec
make_microscopy_focus = optical_tasks.make_microscopy_focus
make_thin_film_endpoint = optical_tasks.make_thin_film_endpoint


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


def test_microscopy_focus_task_has_low_dose_observation_policy():
    task = make_microscopy_focus(
        TaskSpec("synthetic-microscopy-focus", seed=17, split="test", difficulty=1)
    )
    environment = task.environment
    try:
        environment.call("illumination", {"power": 0.3})
        environment.call("exposure", {"seconds": 0.05})
        scores = {}
        for index in range(-6, 7):
            z = index / 4.0
            environment.call("focus", {"z": z})
            result = environment.call("read", {"instrument": "camera"})
            scores[z] = sharpness(result["observations"]["image"]["value"])
        estimate = max(scores, key=scores.get)
        verdict = task.verify({"focus_z_um": estimate})
        assert verdict.passed, verdict.metrics
        assert verdict.metrics["accumulated_dose_mj"] <= 0.24
        assert not task.verify({"focus_z_um": 5.0}).passed
        with pytest.raises(ValueError):
            environment.call("read", {"instrument": "photometer"})
    finally:
        environment.close()


def test_thin_film_task_can_reach_endpoint_from_public_phase():
    task = make_thin_film_endpoint(
        TaskSpec("synthetic-thin-film-endpoint", seed=23, split="test", difficulty=1)
    )
    environment = task.environment
    try:
        environment.call("deposition", {"rate": 1.0})
        environment.call("shutter", {"position": "open"})
        for _ in range(30):
            result = environment.call("read", {"instrument": "interferometer"})
            phase = result["observations"]["phase"]["value"]
            remaining = environment.target_phase_rad - phase
            if remaining <= 0.045:
                break
            if remaining > 0.45:
                seconds = 7.0
            else:
                seconds = max(0.15, min(1.5, remaining * 632.8 / (4.0 * math.pi * 2.0)))
            environment.call("wait", {"seconds": seconds})
        environment.call("shutter", {"position": "closed"})
        verdict = task.verify({"complete": True})
        assert verdict.passed, verdict.metrics
        assert verdict.metrics["thickness_error_nm"] < 3.0
    finally:
        environment.close()

    wrong = make_thin_film_endpoint(
        TaskSpec("synthetic-thin-film-endpoint", seed=23, split="test", difficulty=1)
    )
    try:
        wrong.environment.call("shutter", {"position": "closed"})
        assert not wrong.verify({"complete": True}).passed
    finally:
        wrong.environment.close()


def test_optical_task_entry_points_are_installed():
    names = {entry.name for entry in importlib.metadata.entry_points(group="agent_gym.tasks")}
    assert {"synthetic-thin-film-endpoint", "synthetic-microscopy-focus"} <= names
