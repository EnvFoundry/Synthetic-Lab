"""Compare two observation-based controllers across independent synthetic heaters."""

import json

import numpy as np

from synthetic_lab.integrations.gymnasium import ThermalControlEnv


def main():
    scores = {}
    for controller in ("constant", "feedback"):
        returns = []
        for seed in range(5):
            env = ThermalControlEnv()
            obs, _ = env.reset(seed=seed)
            total = 0.0
            for _ in range(env.max_steps):
                voltage = (
                    4.0
                    if controller == "constant"
                    else np.clip(3.8 + 0.5 * (env.target_k - obs[0]), 0, 5)
                )
                obs, reward, terminated, truncated, _ = env.step(
                    np.array([voltage], dtype=np.float32)
                )
                total += reward
                if terminated or truncated:
                    break
            returns.append(total)
            env.close()
        scores[controller] = {"returns": returns, "mean_return": float(np.mean(returns))}
    print(
        json.dumps(
            {"source": "simulation", "task": "thermal-control-v1", "scores": scores}, indent=2
        )
    )


if __name__ == "__main__":
    main()
