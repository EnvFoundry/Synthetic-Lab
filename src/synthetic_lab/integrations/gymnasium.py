"""A finite-budget thermal control task over the open laboratory API."""

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ..runtime import Lab


class ThermalControlEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, target_k=305.15, max_steps=200):
        if not 298 <= target_k <= 310:
            raise ValueError("target_k must be in [298, 310]")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.target_k = float(target_k)
        self.max_steps = max_steps
        self.action_space = spaces.Box(0, 5, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(4,), dtype=np.float64)
        self.lab = None
        self.experiment = None
        self.steps = 0

    def _observation(self):
        response = self.experiment.act("read")
        values = response["observations"]
        observation = np.array(
            [values[key]["value"] for key in ("temperature", "ambient", "voltage", "current")],
            dtype=np.float64,
        )
        return observation, {
            "elapsed_s": response["end_s"],
            "target_k": self.target_k,
            "source": "simulation",
        }

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options:
            raise ValueError("No reset options are supported")
        self.close()
        self.lab = Lab(":memory:")
        specimen_seed = int(self.np_random.integers(0, 2**63 - 1))
        self.experiment = self.lab.create("thermal", seed=specimen_seed)
        self.experiment.act("connect", channel="ambient")
        self.experiment.act("connect", channel="electrical")
        self.steps = 0
        return self._observation()

    def step(self, action):
        if self.experiment is None or self.steps >= self.max_steps:
            raise RuntimeError("Call reset before starting another episode")
        values = np.asarray(action, dtype=np.float32)
        if not self.action_space.contains(values):
            raise ValueError("Action must have shape (1,) with a voltage in [0, 5]")
        self.experiment.act("supply", voltage=float(values[0]))
        self.experiment.act("wait", seconds=5.0)
        self.steps += 1
        observation, info = self._observation()
        error = float(observation[0] - self.target_k)
        reward = -((error / 10) ** 2) - 0.001 * float(values[0]) ** 2
        return observation, reward, False, self.steps >= self.max_steps, info

    def close(self):
        if self.lab is not None:
            self.lab.close()
        self.lab = None
        self.experiment = None
