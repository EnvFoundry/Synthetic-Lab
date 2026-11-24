# Interfaces

## Command line

The `--db` option precedes the subcommand. Use an absolute path when an agent host starts in a different directory.

```sh
synthetic-lab --db runs/lab.sqlite list
synthetic-lab --db runs/lab.sqlite create thermal --id heater --seed 31
synthetic-lab --db runs/lab.sqlite act heater connect '{"channel":"electrical"}'
synthetic-lab --db runs/lab.sqlite act heater supply '{"voltage":4}' --operation-id supply-1
synthetic-lab --db runs/lab.sqlite act heater wait '{"seconds":600}' --operation-id settle-1
synthetic-lab --db runs/lab.sqlite act heater read
synthetic-lab --db runs/lab.sqlite fork heater --id comparison
synthetic-lab --db runs/lab.sqlite status heater
synthetic-lab --db runs/lab.sqlite export heater runs/heater.jsonl
```

Use unique session IDs when running these commands again, or continue an existing session. Each command emits JSON. Invalid actions return an error and leave the simulation state unchanged.

`synthetic-lab --db runs/lab.sqlite serve` reads JSON requests on stdin and writes one result per line. The envelope has `id`, `method` and `params`. This is the project's line protocol. Supported methods are `catalogue`, `sessions`, `create`, `status`, `act`, `fork` and `history`.

```json
{"id":1,"method":"act","params":{"session_id":"heater","action":"read","params":{},"operation_id":"read-1"}}
```

## MCP

Install `.[agent]`. Configure a stdio-compatible host with the executable and an absolute experiment database path. The exact host configuration filename depends on the agent application.

```json
{
  "mcpServers": {
    "synthetic-lab": {
      "command": "synthetic-lab",
      "args": ["--db", "/absolute/path/research.sqlite", "mcp"]
    }
  }
}
```

The seven tools are `laboratories`, `sessions`, `create`, `observe_configuration`, `operate`, `fork` and `history`. The catalogue describes valid action names, parameter bounds and units. `operate` requires an operation ID so that a host can retry after losing a response. MCP calls and Python calls use the same runtime. The test suite initializes a stdio client, discovers tools, creates a laboratory and acquires a measurement through this interface.

This configuration gives its host control over the research database. For a benchmark, provide the episode's permitted tools and keep its database with the evaluator. The `agent_gym` adapter implements that arrangement for thermal identification.

## Gymnasium and policy learning

```sh
python -m pip install -e '.[rl]'
python examples/train_control.py
python examples/learn_control.py
```

```python
import numpy as np
from synthetic_lab.integrations.gymnasium import ThermalControlEnv

env = ThermalControlEnv(target_k=305.15, max_steps=200)
observation, info = env.reset(seed=7)
try:
    finished = False
    while not finished:
        voltage = float(np.clip(3.8 + 0.5 * (305.15-observation[0]), 0, 5))
        observation, reward, terminated, truncated, info = env.step(
            np.array([voltage], dtype=np.float32)
        )
        finished = terminated or truncated
finally:
    env.close()
```

The action is commanded voltage in V, represented as a float32 array of shape `(1,)` in `[0, 5]`. The observation is a float64 array containing sample temperature in K, ambient temperature in K, voltage in V and current in A. It contains measured channels. Gaussian sensor noise gives mathematically unbounded observations, so the declared observation space is unbounded. RL libraries may apply their own observation normalization or normalized-action wrapper.

One step sets the supply, waits 5 simulated seconds, and measures. Including the action and read durations, it advances 5.22 s. Reward is `-((measured_temperature-target)/10)**2 - 0.001*commanded_voltage**2`. The ongoing control task has no intrinsic terminal state; its finite action budget sets `truncated=True`. Physical reachability of the requested temperature depends on the specimen's parameters. Use the public observations to adapt to a different heater.

`train_control.py` compares fixed and feedback controllers. `learn_control.py` actually optimizes a feedback policy using cross-entropy search over bias and gain. It uses two training seeds, three generations of eight candidates, and five held-out seeds. It writes learned parameters and every test return to `runs/learned-control.json`. These are small simulation experiments for checking the learning path.

For parallel sampling, construct an independent `ThermalControlEnv` for each Gymnasium vector slot. Each environment owns its database. This avoids sharing mutable specimen state or overwriting another episode on reset. Resetting a public research session would discard its history, so research sessions instead use `create` or `fork` explicitly.

## Verifiable Agent Gym

Install this project and [Verifiable Agent Gym](https://github.com/EnvFoundry/Verifiable-Agent-Gym) in the host environment. The `agent_gym.tasks` entry point registers `synthetic-thermal`.

```sh
agent-gym list
```

The task gives the agent temperature readout, optional electrical and ambient channels, adjustable voltage and waiting. It asks for thermal resistance with 0.5 K/W absolute tolerance and permits 24 actions. The task generator uses the task's split and seed to select a specimen. Its hidden reference value stays in the verifier. The test suite solves it using measurements, checks a wrong answer, and rejects an operation outside the allowed task tools.

Closing this environment releases its own simulation. Physical instruments remain managed by IOP. The integration has been exercised against the upstream revision pinned in `.github/workflows/test.yml`.

## Observations, calibration and data export

`Session.export(path)` writes an operation JSONL file with schema version 1. Each row contains the session, lineage, operation ID, action, normalized parameters, model version, simulation interval, observations and visible settings. Source labels are explicit. Latent state and random-state snapshots stay in the database. The branch's parent and source revision are available through `status`.

Group related branches by lineage when forming dataset splits. Group empirical records by the relevant device, batch or date when measuring generalization. Data Engineering can ingest these records through a source adapter appropriate to its own record schema.

To fit from empirical thermal data, construct records with `source="measurement"` and four unit-bearing observations named `temperature`, `ambient`, `voltage` and `current`. Select settled measurements at distinct power levels with common contact and ambient conditions. Provide their session and operation references. `fit_thermal` also accepts the native simulated records and rejects a mixture of the two source types in one fit.

```python
import json
from synthetic_lab import Lab
from synthetic_lab.calibration import fit_thermal

with open("settled-measurements.jsonl", encoding="utf-8") as file:
    records = [json.loads(line) for line in file if line.strip()]
fit = fit_thermal(records)
with Lab("runs/calibrated.sqlite") as lab:
    experiment = lab.create(
        "thermal",
        config={"thermal_resistance": fit["thermal_resistance_k_per_w"], "variation": 0},
        provenance={"source": fit["source"], "reference": "settled-measurements.jsonl",
                    "method": "steady-state regression", "power_range_w": fit["power_range_w"]},
    )
    print(experiment.status())
```

The example expects a user-supplied file. The fit reports an intercept, residual error and input references. Hold back measurements before fitting and test their predictions independently. Creating a new calibrated model preserves the earlier experiment. New observations from it retain `source="simulation"`, while `model_provenance` identifies the data used to configure it.
