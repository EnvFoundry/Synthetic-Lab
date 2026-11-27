# Synthetic Lab

**Persistent, physics-grounded laboratories for open-ended research.**

[中文](README.zh-CN.md) · [Laboratory atlas](docs/lab-atlas.md) ·
[Research contract](docs/research-contract.md) · [Architecture](docs/design.md) ·
[Agent and RL interfaces](docs/interfaces.md) · [Language interfaces](docs/platform.md) ·
[Contribute](CONTRIBUTING.md)

Synthetic Lab gives people and AI agents the same experimental surface: change an apparatus,
wait for physical state to evolve, acquire finite and noisy measurements, continue later, or fork
an earlier state to compare interventions. Sessions retain time, hidden specimen state and random
state across process restarts.

A laboratory exposes controls and a machine-readable **research contract**: the questions
it can investigate, observables, latent variables, interventions, invariants, validity conditions,
limitations and reference methods. Agents can discover this information through the same catalogue
used by Python, CLI and MCP clients.

## Run an experiment

Python 3.11 or later. The core runtime uses the standard library.

```sh
git clone https://github.com/EnvFoundry/Synthetic-Lab.git
cd Synthetic-Lab
python -m pip install -e .
python examples/open_research.py
python examples/optimize_reaction.py
python -m pip install -e labs/optical-metrology
python examples/coat_thin_film.py
python examples/adaptive_microscopy.py
python -m pip install -e labs/spectroscopic-bioprocess
python examples/optimize_bioprocess.py
```

```python
from synthetic_lab import Lab

with Lab("runs/research.sqlite") as lab:
    experiment = lab.create("reaction", seed=13)
    experiment.act("set_temperature", setpoint={"value": 92, "unit": "degC"})
    experiment.act("wait", seconds=600, operation_id="stage-1")
    spectrum = experiment.act("read", instrument="spectrometer")
    alternative = experiment.fork()
    alternative.act("set_temperature", setpoint=320)
    print(spectrum["observations"])
```

Reopen the database and call `lab.session(saved_id)` to continue. Reusing an operation identifier
with the same request returns its recorded result. `expected_revision` rejects a decision made
against an older apparatus state. Every result records its model identifier, simulation interval,
normalized parameters, units, provenance and visible configuration.

Long calculations can continue independently of the submitting client:

```sh
# Submit from a client process.
synthetic-lab --db runs/research.sqlite submit reactor wait '{"seconds":3600}' \
  --operation-id stage-2

# Execute chemistry operations in a separate environment or host.
synthetic-lab --db runs/research.sqlite worker --model reaction

# Read the operation state and final result.
synthetic-lab --db runs/research.sqlite operation reactor stage-2
```

Submission, claim and result commit use short database transactions. The solver runs in the worker
process without holding the database write lock. Operations on one session remain ordered, while
different sessions can run concurrently. Workers load only the laboratories installed in their own
environment.

## Laboratories

| Laboratory | Experimental problem | Model basis |
|---|---|---|
| `reaction` | Select a temperature programme and measurement schedule to maximize an intermediate while separating kinetics, deactivation and thermal effects | Consecutive Arrhenius reactions, catalyst deactivation and lumped reactor heat balance |
| `fiber` | Find and track a drifting coupling peak; distinguish source variation from alignment loss; choose zeroing and exposure | Gaussian coupling, laser warm-up, drift and finite-range detectors |
| `thermal` | Separate heating power from thermal contact and predict a held-out power or clamp condition | Joule heating, lumped heat capacity and thermal resistance |
| `battery` | Design pulses to identify resistance and relaxation while respecting voltage and temperature limits | Charge balance, one-RC equivalent circuit and self-heating |
| `thin-film` · optical package | Select deposition and anneal endpoints from broadband reflection, phase and temperature | Thin-film interference, growth, porosity, roughness and thermal densification |
| `fluorescence-microscopy` · optical package | Choose focus, stage, channel and photon dose while samples drift and bleach | Diffraction-limited imaging, detector statistics and photobleaching |
| `spectroscopic-bioreactor` · bioprocess package | Coordinate feed, aeration and optical induction from OD, fluorescence, Raman and oxygen measurements | Fed-batch mass balances, Monod growth, oxygen transfer, reporter response and production burden |
| `fluid-tank` · optional package | Infer outlet conductance and predict a held-out inflow programme | Volume balance with linear hydraulic resistance |

These are reference simulations with synthetic parameter priors, not device-specific twins. Their
contracts and model documents state the approximations and failure conditions. A calibrated twin
must name its physical counterpart, data, operating range and held-out predictive performance.
[Reaction model](docs/reaction-lab.md) · [Optical metrology](docs/optical-metrology.md) ·
[Bioprocess spectroscopy](docs/spectroscopic-bioprocess.md) · [Reference models](docs/models.md)

The [frontier laboratory atlas](docs/lab-atlas.md) gives the intended expansion order: materials
synthesis and catalysis, predictive biology, electrochemical energy, semiconductor and photonic
fabrication, scientific imaging, fusion, Earth systems, manufacturing and quantum control.
Domains use independently installable packages sharing the same runtime and contract.
The [domain package catalogue](labs/README.md) lists the available installations.

## Agents, learning and data

| Interface | Workflow |
|---|---|
| Python, CLI and JSON lines | Discover, create, submit, operate, resume, branch, inspect history and export |
| Domain workers | Run long operations in independent dependency environments |
| MCP stdio | The same persistent and queued operations exposed to an agent host |
| Gymnasium | Seeded control environments with explicit action budgets |
| Verifiable Agent Gym | Isolated tasks whose hidden answers stay with the evaluator |
| JSONL and calibration | Unit-bearing traces and model profiles with source references |

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
```

The catalogue returned through these interfaces includes each model's action schema and research
contract. A scored agent receives only the permitted operations and observations; latent specimen
state, random state and evaluator answers remain owner-side.

## Repository structure

| Path | Responsibility |
|---|---|
| `src/synthetic_lab/runtime.py` | Sessions, ordered operation queue, short state transactions, snapshots, forks and streaming export |
| `src/synthetic_lab/worker.py` | Domain-specific operation workers and renewable claims |
| `src/synthetic_lab/research.py` | Cross-domain scientific contract and validation |
| `src/synthetic_lab/models/` | Reference physics, observations and model contracts |
| `src/synthetic_lab/integrations/` | MCP, Gymnasium and Verifiable Agent Gym adapters |
| `src/synthetic_lab/calibration.py` | Fitting from unit-bearing observations with data references |
| `labs/optical-metrology/` | Independently installable fabrication and microscopy laboratories |
| `labs/spectroscopic-bioprocess/` | Independently installable fed-batch and optical process-sensing laboratory |
| `spec/`, `packages/protocol-ts/`, `crates/protocol/` | JSON Schema and TypeScript/Rust bindings exercised with live experimental output |
| `sql/` | Executable relational layout for sessions, operations, claims and snapshots |
| `examples/` | End-to-end research, alignment, pulse, reaction, optical and learning programmes |
| `tests/` | Governing relations, persistence, concurrency and interface behavior |
| `docs/` | Architecture, model scope, laboratory priorities and contribution boundaries |

Within EnvFoundry, IOP owns real instrument execution, domain laboratories own specialized solvers,
SeedEnv prepares dependencies, Gym owns tasks and assessment, and data systems consume traces.
Synthetic Lab owns simulated experimental state and observations. Python currently implements the
worker lifecycle; the shared SQL and protocol boundary permit a Rust service and TypeScript workbench
to use the same operation semantics without duplicating scientific models.

MIT licensed.
