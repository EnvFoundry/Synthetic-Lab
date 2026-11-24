# Synthetic Lab

**Persistent, physics-grounded laboratories for open-ended research.**

[中文](README.zh-CN.md) · [Models](docs/models.md) · [Architecture](docs/design.md) · [Agent and RL interfaces](docs/interfaces.md) · [Contribute](CONTRIBUTING.md)

Enter with a question, operate an instrument, change the apparatus, and continue from the resulting state. Synthetic Lab gives people and AI agents the same experimental operations. A heater remembers its temperature, a battery retains its charge and polarization, and a fiber bench drifts as experiment time passes. Sessions survive process restarts and can branch at a recorded simulation state.

The aim is a growing collection of useful experimental environments across science and engineering, informed by physical models, measurements and domain expertise. Researchers can contribute an independent domain package. Open research, reinforcement learning and evaluation use the same underlying laboratory.

## Run an experiment

Python 3.11 or later. The core uses the standard library.

```sh
git clone https://github.com/EnvFoundry/Synthetic-Lab.git
cd Synthetic-Lab
python -m pip install -e .
python examples/open_research.py
```

This experiment attaches electrical and ambient-temperature measurements to a heater, estimates thermal resistance at three power settings, predicts a held-out setting, and compares two clamp conditions from a common initial state. Results and experiment records go into `runs/`.

```python
from synthetic_lab import Lab

with Lab("runs/my-lab.sqlite") as lab:
    experiment = lab.create("thermal", seed=31)
    experiment.act("connect", channel="electrical")
    experiment.act("connect", channel="ambient")
    experiment.act("supply", voltage={"value": 4000, "unit": "mV"})
    experiment.act("wait", seconds=600, operation_id="settle-1")
    print(experiment.act("read")["observations"])
    print(experiment.id)
    alternative = experiment.fork()
    alternative.act("clamp", contact="loose")
```

Reopen the database and call `lab.session(saved_id)` to continue. Repeating an action with its original operation ID returns its recorded result. Supplying `expected_revision` detects a stale decision from another client. Every observation carries its units, simulation origin, time interval, model version and operation identity.

## Available laboratories

| Laboratory | Experimental questions and effects | Model basis |
|---|---|---|
| `fiber` | Find and track a coupling peak, measure a reference beam, zero a meter, choose camera exposure. Includes warm-up, common source variation, drift, noise and detector clipping | Gaussian coupling and a first-order laser response |
| `thermal` | Separate power changes from heat-transfer changes by adding measurements and changing a clamp | Electrical heating, lumped heat capacity and thermal resistance |
| `battery` | Choose current pulses and rest periods, observe voltage recovery, temperature and protection | Charge balance and a one-RC equivalent circuit with self-heating |
| `fluid-tank` · optional example package | Estimate an outlet conductance from inflow and level, continue or fork an experiment | Volume balance with a linear hydraulic resistance |

The reference models are analytical simulations with stated approximations and synthetic parameter priors. Device-specific physical calibration is a further contribution. The battery model covers pulse response and heating; lifetime and electrochemical degradation require additional models and data. [Equations, noise models and limits](docs/models.md).

```sh
python examples/align_fiber.py
python examples/battery_pulse.py
python -m pip install -e examples/tank-package
synthetic-lab --db runs/lab.sqlite list
```

## Agents, learning and data

| Interface | Available workflow |
|---|---|
| Python, CLI and JSON lines | Discover controls, create a session, operate, resume, branch and export |
| MCP stdio | Seven tools using the same persistent runtime |
| Gymnasium | Thermal control, deterministic seeded reset, vector environments and explicit budget truncation |
| Verifiable Agent Gym | Independently registered thermal-identification task and an observation-based solution test |
| JSONL and calibration | Export observable operations, fit a thermal model from settled signals and retain data references in new model profiles |

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
# In a separate terminal
python examples/learn_control.py
```

The learning example optimizes a feedback policy with cross-entropy search on two training specimens and evaluates five different seeds. It saves the policy, seeds, returns and constant-controller comparison. [Connection examples and task semantics](docs/interfaces.md).

## Repository structure

| Path | Responsibility |
|---|---|
| `src/synthetic_lab/runtime.py` | Transactional sessions, immutable operation results, snapshots, forks and export |
| `src/synthetic_lab/models/` | Reference physics, actions, instruments and observable configuration |
| `src/synthetic_lab/integrations/` | MCP, Gymnasium and Verifiable Agent Gym |
| `src/synthetic_lab/calibration.py` | Fitting from unit-bearing observations with data references |
| `examples/` | Complete research, alignment, pulse-testing, policy-learning and extension programs |
| `tests/` | Physical relations, replay, concurrency, failures and real interface round trips |
| `docs/` | Model assumptions, architecture, contribution boundaries and development direction |

Within EnvFoundry, IOP owns real instrument execution, Optics–Photonics AI Lab provides specialized solvers, and SeedEnv prepares dependencies. Synthetic Lab owns simulated experimental state and observation generation. Gym supplies tasks and rewards. Data Engineering and AI Evaluation can consume the resulting traces through adapters. The current runtime is local Python and SQLite, accessible from a remote agent host through stdio. A shared, multi-user cloud service and device-specific digital twins are development goals. [Implementation status and roadmap](docs/roadmap.md).

MIT licensed. [Project charter and cross-domain requirements](docs/charter.zh-CN.md).
