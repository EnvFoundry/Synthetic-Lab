# Interfaces

## Command line

The `--db` option precedes the subcommand. Use an absolute path when a client starts in a different directory.

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

`act` submits an operation and waits for completion. Long calculations can be submitted without
holding the client process:

```sh
synthetic-lab --db runs/lab.sqlite submit heater wait '{"seconds":3600}' \
  --operation-id long-settle
synthetic-lab --db runs/lab.sqlite operation heater long-settle
synthetic-lab --db runs/lab.sqlite worker --model thermal
```

A worker can load one or several laboratory names. Operations on one session run in submission
order; workers may process different sessions concurrently. The numerical solver runs outside the
database write transaction. Stopping a worker before commit leaves the prior experimental state
unchanged, and another worker can continue the queued operation.

Use unique session IDs when running creation commands again, or continue an existing session. Each
command emits JSON. Invalid actions return an error and leave the simulation state unchanged.

`synthetic-lab --db runs/lab.sqlite serve` reads JSON requests on stdin and writes one result per
line. The envelope has `id`, `method` and `params`. Supported methods are `catalogue`, `sessions`,
`create`, `status`, `act`, `submit`, `operation`, `fork` and `history`.

```json
{"id":1,"method":"submit","params":{"session_id":"heater","action":"wait","params":{"seconds":3600},"operation_id":"long-settle"}}
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

The tools are `laboratories`, `sessions`, `create`, `observe_configuration`, `operate`,
`submit_operation`, `operation_status`, `fork` and `history`. The catalogue describes valid action
names, parameter bounds and units. `operate` waits for a result. `submit_operation` returns a
pending or running operation immediately, and `operation_status` returns its current state and final
result. Operation IDs let a host repeat a request after losing a response without applying the
physical action twice.

MCP calls, CLI calls and Python calls use the same operation table. A separate worker process may
execute operations submitted through any interface.

## Python workers

```python
from synthetic_lab import Lab, Worker

with Lab("runs/lab.sqlite") as lab:
    experiment = lab.create("reaction", seed=31)
    operation = experiment.submit(
        "wait", seconds=1800, operation_id="reaction-stage"
    )

with Lab("runs/lab.sqlite") as lab:
    worker = Worker(lab, models=("reaction",), worker_id="chemistry-1")
    worker.run_once()
    result = lab.operation(operation["session"], operation["operation_id"])
```

`Worker.serve()` processes matching operations continuously. Install each domain package in the
worker environment that owns its solver dependencies. A microscopy worker can therefore use image
libraries and a reaction worker can use chemistry libraries without placing both dependency sets in
the client environment.

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

`train_control.py` compares fixed and feedback controllers. `learn_control.py` optimizes a feedback policy using cross-entropy search over bias and gain. It uses two training seeds, three generations of eight candidates, and five held-out seeds. It writes learned parameters and every held-out return to `runs/learned-control.json`.

For parallel sampling, construct an independent `ThermalControlEnv` for each Gymnasium vector slot. Each environment owns its database. Public research sessions instead use `create` or `fork` explicitly so their histories remain available.

## Verifiable Agent Gym

Install this project and [Verifiable Agent Gym](https://github.com/EnvFoundry/Verifiable-Agent-Gym) in the host environment. The `agent_gym.tasks` entry point registers `synthetic-thermal`.

```sh
agent-gym list
```

The task gives the agent temperature readout, optional electrical and ambient channels, adjustable voltage and waiting. It asks for thermal resistance with 0.5 K/W absolute tolerance and permits 24 actions. The task generator uses the task's split and seed to select a specimen. Its hidden reference value stays with the evaluator.

Closing this environment releases its own simulation. Physical instruments remain managed by IOP.

## Observations, calibration and data export

`Session.export(path)` streams completed operations to JSONL in bounded batches. Each row contains
the session, lineage, operation ID, action, normalized parameters, model identifier, simulation
interval, observations and visible settings. Latent state and random-state snapshots stay in the
database. `Lab.iter_history()` supports incremental consumers without loading a complete long
experiment into memory.

Large images, fields and trajectories still need an external data store rather than inline JSON.
The operation result is the place for a compact reference, shape, units and acquisition metadata;
the next storage layer will implement that reference without changing domain equations.

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

The example expects a user-supplied file. The fit reports an intercept, residual error and input references. Hold back measurements before fitting and compare their predictions independently. Creating a new calibrated model preserves the earlier experiment. New observations from it retain `source="simulation"`, while `model_provenance` identifies the data used to configure it.
