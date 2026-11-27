# Development direction

Synthetic Lab should let a researcher investigate valuable phenomena for as long as the question
requires. Its common structure is experimental objects, actions, observations, time and history.
Domain experts supply the science and the conditions under which a prediction can be trusted.

## Current implementation

Version 0.2 has four built-in reference laboratories, two optical-metrology laboratories, a
spectroscopic fed-batch bioreactor, an independently packaged fluid-tank example, three
PyBaMM-backed battery laboratories, one Meep-backed photonic-cavity laboratory, and two PhysiCell
multicellular laboratories: a two-dimensional organoid section and a three-dimensional CAR-T spheroid.

The PyBaMM family receives one persistent current protocol through SPM, SPMe and DFN. The Meep
package receives a commanded cavity design, draws one hidden fabricated geometry, normalizes its
transmission against a straight waveguide and returns spectra, resonances and field maps. Their
equations, spatial discretisation and numerical methods remain in the upstream scientific software.

All laboratories expose research questions, instruments, physical relations and assumptions through
the same catalogue. Persistent sessions, experiment branches, CLI, MCP, Gymnasium and Verifiable
Agent Gym reuse the local runtime. JSON Schema, TypeScript and Rust describe the public data boundary
and are exercised with live experimental output. Domain workers execute queued operations outside
database write transactions. Existing sessions can be used by clients without domain dependencies.
Large state and observation arrays have external JSON storage; histories and data can be read
incrementally.

The built-in and first-party reduced-order models use synthetic priors or supplied configurations.
The PyBaMM family uses the `Chen2020` parameter set and is not calibrated to a named cell. The Meep
cavity uses a two-dimensional, lossless and nondispersive dielectric representation and is not
calibrated to a fabricated chip.

PhysiCell/BioFVM supplies cell dynamics and transport. Domain callbacks add heterogeneous drug
response, antigen-dependent CAR attachment and killing, and continuous exhaustion. Both packages
run whole-culture endpoint assays. They have no instrument noise model or mid-culture continuation.

## Scientific software expansion

New capability should normally come from a domain adapter to a mature solver, dataset or real
instrument system. The adapter owns persistent experimental state, action translation, selected
observations, units and continuation. It does not copy the upstream solver into this repository.

The next photonics work should give transfer-matrix and RCWA packages the same materials, geometry,
illumination and detector description already used by the Meep experiment. The first comparison
should use structures all methods can represent, quantify spectral disagreement and computation
cost, and identify conditions where the cheaper method changes the selected design.

| Domain | Existing software to reuse | First consequential experiment |
|---|---|---|
| Wave optics and photonics | Transfer matrix, RCWA and Meep | Choose spectral measurements and designs while escalating fidelity only when model disagreement changes the decision |
| Reaction engineering | Cantera | Infer kinetics from spectroscopy, then predict a held-out temperature and flow programme |
| Continuum transport | FEniCS or OpenFOAM | Distinguish lumped and spatial thermal or fluid models using sensor placement and transient forcing |
| Molecular systems | OpenMM or LAMMPS | Choose restrained simulations that separate competing molecular states under a compute budget |
| Quantum control | QuTiP | Infer drift and design pulses that remain effective on held-out device parameters |

An adapter should make a consequential intervention executable and support continuation after a
physical termination where the experimental object remains usable. Whole-assay models must state
their terminal boundary explicitly. When comparable model families exist, run the same intervention at multiple
fidelities. Task generation should follow a meaningful model or measurement choice; a useful solver
integration does not require inventing a second model solely to populate a comparison.

## Experiments that would extend its scientific value

The current solver integrations make three concrete extensions possible: preserve native battery
state for long cycling; compare optical solvers on a common geometry they all represent; and split
cell culture into resumable intervals with intermediate observations and new interventions. For
the culture packages, estimate variation across seeds before interpreting a selected receptor design
or dose. Add measured cell counts, spatial distributions and sensor response when fitting a named assay.
These changes should precede adding more variants of an existing endpoint experiment.

| Contribution | Concrete experiment and expected deliverable |
|---|---|
| Calibrated photonic device | Import measured refractive index, SEM geometry and spectrometer response for named devices; predict spectra and resonances of devices not used to fit them |
| Calibrated optical bench | Measure repeatability, detector response, drift and coupling curves from a named bench; predict held-out movements and exposure changes in physical units |
| Battery cell calibration | Fit a named cell's open-circuit, thermal and transport parameters on selected protocols, then compare SPM, SPMe and DFN on later pulses and drive cycles |
| Thermal and fluid devices | Compare a one-body model with a distributed solver under transients; change sensor placement when the models disagree measurably |
| Materials and fabrication | Follow one identified sample through fabrication, spectroscopy and thermal cycling; predict which remaining process change can correct a measured deviation |
| Energy and aging | Add degradation and temperature-dependent impedance; use later cycle data to assess predictions from short test sequences |
| Mechanics and assembly | Model contact, friction, compliance and measurement limits; reproduce an assembly across held-out component tolerances |
| Scientific imaging | Add optical transfer, exposure history and bleaching or drift supported by measurements; compare information gained per sample dose |
| Environmental experiments | Include evolving boundary conditions and observation windows; compare sampling plans under measured spatial and temporal correlations |

Each addition should include an independent user's experiment, an executable reference method,
recorded assumptions, a held-out condition and the physical meaning of its outputs. An early
analytical model is useful when its scope is explicit. An empirical fidelity claim needs the
corresponding real-world comparison.

## Shared infrastructure to grow with use

Cross-domain sample transfer needs stable sample identity, ownership of each state variable and an
executable coupled example. Multi-rate co-simulation needs time synchronization and exchanged
boundary conditions. Integration with IOP needs operation reconciliation after uncertain outcomes,
shared resource ownership and device-limited timing. A digital twin needs a named physical
counterpart, model updates from new measurements and demonstrated use of its predictions in later
experiments.

A multi-host cloud deployment still needs a server database, remote object storage and a service
interface suited to its users and compute resources. The current queued workers and external JSON
store provide same-host execution. The local runtime provides experiment semantics that a service
can reuse. Scheduling real hardware remains with its device runtime. Separate independent training
workers can scale simulation before adding shared coordination.

## Research and evaluation

Keep fixed reference experiments so progress remains comparable. Add new batches, devices and
challenging interventions as separate task populations. Keep calibration and model selection away
from the observations used to assess them. Include appropriate domain methods alongside agent
baselines, and report physical results, experiment time, specimen use and computational cost.

An experiment that distinguishes two plausible models can be more valuable than a higher score on an
already-solved task. Preserve failed attempts when they identify a useful constraint or rule out a
design.
