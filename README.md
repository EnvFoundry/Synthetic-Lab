# Synthetic Lab

**Persistent, physics-grounded laboratories for open-ended research.**

[中文](README.zh-CN.md) · [Laboratory atlas](docs/lab-atlas.md) ·
[Research contract](docs/research-contract.md) · [Architecture](docs/design.md) ·
[Solver-backed laboratories](docs/solver-backed-laboratories.md) ·
[Agent and RL interfaces](docs/interfaces.md) · [Language interfaces](docs/platform.md) ·
[External data](docs/artifacts.md) · [Contribute](CONTRIBUTING.md)

Synthetic Lab gives people and AI agents the same experimental surface: change an apparatus,
wait for physical state to evolve, acquire observations, continue later, or fork an earlier state
to compare interventions. Sessions retain time, hidden specimen state and random state across
process restarts. Each laboratory declares its measurement response, noise and time cost.

A laboratory exposes controls and a machine-readable **research contract**: the questions it can
investigate, observables, latent variables, interventions, invariants, validity conditions,
limitations and reference methods. Python, CLI and MCP clients discover the same description.

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
python -m pip install -e labs/pybamm-battery
python examples/compare_pybamm_models.py
```

Meep is installed from conda-forge:

```sh
conda env create -f labs/meep-photonics/environment.yml
conda activate synthetic-lab-meep
python -m pip install -e . -e labs/meep-photonics
python examples/measure_photonic_cavity.py
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
synthetic-lab --db runs/research.sqlite create reaction --id reactor
synthetic-lab --db runs/research.sqlite submit reactor wait '{"seconds":3600}' \
  --operation-id stage-2
synthetic-lab --db runs/research.sqlite worker --model reaction
synthetic-lab --db runs/research.sqlite operation reactor stage-2
```

Submission, claim and result commit use short database transactions. The solver runs in the worker
process without holding the database write lock. Operations on one session remain ordered, while
different sessions can run concurrently. Workers load only the laboratories installed in their own
environment.

Large images, spectra, fields and trajectories are stored beside the experiment database. Operation
records keep compact references, units, shape, axes and acquisition metadata; clients retrieve the
array only when needed. Unchanged large state is shared across successive operations and branches.

Mature numerical software remains in its own domain package. Synthetic Lab translates persistent
operations into solver inputs and selected solver variables into observations:

- PyBaMM supplies SPM, SPMe and DFN electrochemistry for one shared battery protocol;
- Meep supplies full-wave time-domain Maxwell solutions for a fabricated photonic-crystal cavity.

The Meep laboratory separates commanded design from hidden fabricated geometry, normalizes cavity
transmission against a straight-waveguide reference, extracts resonance properties and stores a
resonant two-dimensional field map through the external-data layer.

Existing sessions retain their public action descriptions. A client can submit operations and read
configurations without installing the domain solver. Creation and local `act` calls require the
domain package. SQLite workers currently share one host.

## Laboratories

| Laboratory | Experimental problem | Model basis |
|---|---|---|
| `reaction` | Select a temperature programme and measurement schedule to maximize an intermediate while separating kinetics, deactivation and thermal effects | Consecutive Arrhenius reactions, catalyst deactivation and lumped reactor heat balance |
| `fiber` | Find and track a drifting coupling peak; distinguish source variation from alignment loss; choose zeroing and exposure | Gaussian coupling, laser warm-up, drift and finite-range detectors |
| `thermal` | Separate heating power from thermal contact and predict a held-out power or clamp condition | Joule heating, lumped heat capacity and thermal resistance |
| `battery` | Design pulses to identify resistance and relaxation while respecting voltage and temperature limits | Charge balance, one-RC equivalent circuit and self-heating |
| `pybamm-battery-spm` · solver package | Explore many current protocols quickly and compare them with richer cell models | PyBaMM single-particle model with lumped thermal dynamics |
| `pybamm-battery-spme` · solver package | Study when electrolyte transport changes voltage and protocol decisions | PyBaMM single-particle model with electrolyte and lumped thermal dynamics |
| `pybamm-battery-dfn` · solver package | Resolve porous-electrode transport under the same protocol used by SPM and SPMe | PyBaMM Doyle–Fuller–Newman model with lumped thermal dynamics |
| `meep-photonic-cavity` · solver package | Design, fabricate and measure a photonic-crystal cavity under hidden geometric variation | Meep two-dimensional FDTD, reference-normalized transmission and resonant field imaging |
| `thin-film` · optical package | Select deposition and anneal endpoints from broadband reflection, phase and temperature | Thin-film interference, growth, porosity, roughness and thermal densification |
| `fluorescence-microscopy` · optical package | Choose focus, stage, channel and photon dose while samples drift and bleach | Diffraction-limited imaging, detector statistics and photobleaching |
| `spectroscopic-bioreactor` · bioprocess package | Coordinate feed, aeration and optical induction from OD, fluorescence, Raman and oxygen measurements | Fed-batch mass balances, Monod growth, oxygen transfer, reporter response and production burden |
| `fluid-tank` · optional package | Infer outlet conductance and predict a held-out inflow programme | Volume balance with linear hydraulic resistance |

The built-in and reduced-order packages use synthetic parameter priors. PyBaMM and Meep provide
established numerical solvers, but their generic configurations are not device-specific twins. A
calibrated twin must name its physical counterpart, measured data, operating range and predictive
performance on conditions not used for fitting. [Reaction model](docs/reaction-lab.md) ·
[Optical metrology](docs/optical-metrology.md) ·
[Meep photonics](docs/meep-photonics.md) ·
[Bioprocess spectroscopy](docs/spectroscopic-bioprocess.md) ·
[PyBaMM battery laboratories](labs/pybamm-battery/README.md) · [Reference models](docs/models.md)

The [frontier laboratory atlas](docs/lab-atlas.md) describes the long-term research scope. The
[development direction](docs/roadmap.md) sets current priorities. Domains use independently
installable packages sharing the same runtime and contract; the [domain package catalogue](labs/README.md)
lists their installation paths.

## Agents, learning and data

| Interface | Workflow |
|---|---|
| Python, CLI and JSON lines | Discover, create, submit, operate, resume, branch, inspect history and export |
| Domain workers | Run long operations in independent dependency environments |
| MCP stdio | Expose the same persistent and queued operations to an agent host |
| Gymnasium | Seeded control environments with explicit action budgets |
| Verifiable Agent Gym | Tasks whose hidden answers remain with the evaluator |
| External artifacts | Chunked images, spectra, fields and trajectories outside SQLite |
| JSONL and calibration | Unit-bearing traces and model profiles with source references |

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
```

The catalogue includes each model's action schema and research contract. A scored agent receives
only permitted operations and observations; latent specimen state, random state and evaluator
answers remain owner-side.

## Repository structure

| Path | Responsibility |
|---|---|
| `src/synthetic_lab/runtime.py` | Sessions, ordered operation queue, short state transactions, snapshots, forks and streaming export |
| `src/synthetic_lab/worker.py` | Domain-specific operation workers and renewable claims |
| `src/synthetic_lab/artifacts.py` | Streamed storage for large state and observations |
| `src/synthetic_lab/research.py` | Cross-domain scientific contract |
| `src/synthetic_lab/models/` | Reference physics, observations and model contracts |
| `src/synthetic_lab/integrations/` | MCP, Gymnasium and Verifiable Agent Gym adapters |
| `src/synthetic_lab/calibration.py` | Fitting from unit-bearing observations with data references |
| `labs/meep-photonics/` | Meep full-wave photonic-cavity spectroscopy |
| `labs/pybamm-battery/` | PyBaMM SPM, SPMe and DFN battery laboratories |
| `labs/optical-metrology/` | Fabrication and microscopy laboratories |
| `labs/spectroscopic-bioprocess/` | Fed-batch and optical process-sensing laboratory |
| `spec/`, `packages/protocol-ts/`, `crates/protocol/` | JSON Schema and TypeScript/Rust bindings exercised with live experimental output |
| `sql/` | Relational layout for sessions, operations, claims, snapshots and artifact metadata |
| `examples/` | End-to-end research programmes |
| `tests/` | Governing relations, persistence, concurrency and interface behaviour |
| `docs/` | Architecture, solver boundaries, model scope and laboratory priorities |

Within EnvFoundry, IOP owns real instrument execution, domain laboratories own specialized solvers,
SeedEnv prepares dependencies, Gym owns tasks and assessment, and data systems consume traces.
Synthetic Lab owns simulated experimental state and observations. Python currently implements the
worker lifecycle; the shared SQL and protocol boundary permit a Rust service and TypeScript workbench
to use the same operation semantics without duplicating scientific models.

MIT licensed.
