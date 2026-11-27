# Development direction

Synthetic Lab should let a researcher investigate valuable phenomena for as long as the question requires. Its common structure is experimental objects, actions, observations, time and history. Domain experts supply the science and the conditions under which a prediction can be trusted.

## Current implementation

Version 0.2 has four built-in reference laboratories, two optical-metrology laboratories, a
spectroscopic fed-batch bioreactor, an independently packaged fluid-tank example, and three
PyBaMM-backed battery laboratories. The battery package is the first integration of an established
scientific solver family: SPM, SPMe and DFN receive the same persistent current protocol and expose
the same electrical, thermal and state observations. Their equations and numerical methods remain
in PyBaMM.

All laboratories expose research questions, instruments, physical relations and assumptions through
the same catalogue. Persistent sessions, experiment branches, CLI, MCP, Gymnasium and Verifiable
Agent Gym reuse the local runtime. JSON Schema, TypeScript and Rust describe the public data boundary
and are exercised with live experimental output. Domain workers execute queued operations outside
database write transactions. Existing sessions can be used by clients without domain dependencies.
Large state and observation arrays have external JSON storage; histories and data can be read
incrementally. The optical package supplies thin-film endpoint and dose-limited focus tasks alongside
the thermal task.

The built-in and first-party reduced-order models use synthetic priors or supplied configurations.
The PyBaMM family uses the `Chen2020` parameter set and is not calibrated to a named cell. Its present
continuation strategy replays the committed current protocol in a fresh solver process; long cycling
should later store solver-native restart state as an external experiment object.

## Scientific software expansion

New capability should normally come from a domain adapter to a mature solver, dataset or real
instrument system. The adapter owns persistent experimental state, action translation, selected
observations, units and continuation. It does not copy the upstream solver into this repository.

Strong next integrations are:

| Domain | Existing software to reuse | First consequential experiment |
|---|---|---|
| Wave optics and photonics | Meep, RCWA or an equivalent Maxwell solver | Compare adaptive spectral measurements and inverse designs across transfer-matrix, RCWA and FDTD fidelity |
| Reaction engineering | Cantera | Infer kinetics from spectroscopy, then predict a held-out temperature and flow programme |
| Continuum transport | FEniCS or OpenFOAM | Distinguish lumped and spatial thermal or fluid models using sensor placement and transient forcing |
| Molecular systems | OpenMM or LAMMPS | Choose restrained simulations that separate competing molecular states under a compute budget |
| Quantum control | QuTiP | Infer drift and design pulses that remain effective on held-out device parameters |

A new adapter should first make one shared intervention executable across at least two fidelity levels.
Broader task generation follows after that experiment exposes a meaningful model or measurement
choice.

## Experiments that would extend its scientific value

| Contribution | Concrete experiment and expected deliverable |
|---|---|
| Calibrated optical bench | Measure repeatability, detector response, drift and coupling curves from a named bench. Fit on selected runs, predict held-out movements and exposure changes, and state errors in mrad, W and camera counts |
| Battery cell calibration | Fit a named cell's open-circuit, thermal and transport parameters on selected protocols, then compare SPM, SPMe and DFN on later pulses and drive cycles |
| Thermal and fluid devices | Compare a one-body model with a distributed solver under transients. Add a second thermometer or change a flow boundary when the models disagree measurably |
| Materials and fabrication | Follow one identified sample through fabrication, spectroscopy and thermal cycling. Predict which remaining process change can correct a measured deviation |
| Energy and aging | Add degradation and temperature-dependent impedance. Use later cycle data to assess predictions from short test sequences |
| Mechanics and assembly | Model contact, friction, compliance and measurement limits. Reproduce an assembly across held-out component tolerances |
| Scientific imaging | Add optical transfer, exposure history and bleaching or drift supported by measurements. Let a researcher change acquisition strategy and compare information gained per sample dose |
| Environmental experiments | Include evolving boundary conditions and observation windows. Compare sampling plans under measured spatial and temporal correlations |

Each addition should include an independent user's experiment, an executable reference method,
recorded assumptions, a held-out condition and the physical meaning of its outputs. An early
analytical model is useful when its scope is explicit. An empirical fidelity claim needs the
corresponding real-world comparison.

## Shared infrastructure to grow with use

Cross-domain sample transfer needs stable sample identity, ownership of each state variable and an
executable coupled example. Multi-rate co-simulation needs time synchronization, exchanged boundary
conditions and a measured coupling error. Integration with IOP needs operation reconciliation after
uncertain outcomes, shared resource ownership and device-limited timing. A digital twin needs a named
physical counterpart, model updates from new measurements and a demonstrated use of its predictions
in subsequent experiments.

A multi-host cloud deployment still needs a server database, remote object storage and a service
interface suited to its users and compute resources. The current queued workers and external JSON
store provide same-host execution. The local runtime provides experiment semantics that a service
can reuse. Scheduling real hardware remains with its device runtime. Separate independent training
workers can scale simulation before adding shared coordination.

## Keeping research and evaluation useful

Preserve fixed reference experiments so progress remains comparable. Add new batches, devices and
challenging interventions as separate task populations. Keep calibration and model selection away
from the observations used to assess them. Include appropriate domain methods alongside agent
baselines, and report physical results, experiment time, specimen use and computational cost.

When a physical correction changes an answer, update the model implementation and rerun the relevant
methods. An experiment that distinguishes two plausible models can be more valuable than a higher
score on an already-solved task. Preserve failed attempts when they identify a useful constraint or
rule out a design.
