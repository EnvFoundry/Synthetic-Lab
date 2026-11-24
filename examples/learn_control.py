"""Train a two-parameter policy with cross-entropy search and test new specimens."""

import json
from pathlib import Path

import numpy as np

from synthetic_lab.integrations.gymnasium import ThermalControlEnv


def episode(parameters, seed):
    env = ThermalControlEnv(max_steps=100)
    observation, _ = env.reset(seed=seed)
    total = 0.0
    try:
        for _ in range(env.max_steps):
            voltage = np.clip(parameters[0] + parameters[1] * (env.target_k - observation[0]), 0, 5)
            observation, reward, terminated, truncated, _ = env.step(
                np.array([voltage], dtype=np.float32)
            )
            total += reward
            if terminated or truncated:
                break
    finally:
        env.close()
    return total


def main():
    rng = np.random.default_rng(21)
    mean = np.array([3.5, 0.5])
    spread = np.array([0.8, 0.4])
    training_seeds = [10, 11]
    rounds = []
    for generation in range(3):
        policies = np.clip(rng.normal(mean, spread, size=(8, 2)), [0, 0], [5, 2])
        scores = [
            np.mean([episode(policy, seed) for seed in training_seeds]) for policy in policies
        ]
        elite = policies[np.argsort(scores)[-3:]]
        mean = elite.mean(axis=0)
        spread = np.maximum(elite.std(axis=0), [0.1, 0.05])
        rounds.append({"generation": generation, "best_training_return": float(max(scores))})
    test_seeds = [101, 102, 103, 104, 105]
    baseline = [episode([4, 0], seed) for seed in test_seeds]
    learned = [episode(mean, seed) for seed in test_seeds]
    report = {
        "algorithm": "cross-entropy policy search",
        "source": "simulation",
        "training_seeds": training_seeds,
        "held_out_seeds": test_seeds,
        "policy": {"bias_v": float(mean[0]), "feedback_v_per_k": float(mean[1])},
        "rounds": rounds,
        "baseline_returns": baseline,
        "learned_returns": learned,
        "baseline_mean": float(np.mean(baseline)),
        "learned_mean": float(np.mean(learned)),
    }
    Path("runs").mkdir(exist_ok=True)
    Path("runs/learned-control.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
