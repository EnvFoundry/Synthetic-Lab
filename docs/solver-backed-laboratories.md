# Solver-backed laboratories

Synthetic Lab does not reimplement mature numerical science. A domain package owns the translation
between persistent experimental operations and an established solver. The common runtime retains
session identity, simulation time, branching, queued execution, observations and large data; the
solver retains its equations, discretisation and numerical methods.

| Owner | Responsibility |
|---|---|
| Researcher or task | Scientific question, interventions, measurement choices and budget |
| Synthetic Lab runtime | Sessions, ordered operations, committed state, branches and external data |
| Domain adapter | Persistent experimental object, solver inputs, continuation, units and observation formation |
| Scientific software | Equations, parameterisation, spatial discretisation and numerical integration |

A useful adapter must add more than a subprocess call. It defines:

- the experimental object and hidden state that persist between operations;
- how public controls become solver boundary conditions or protocols;
- which solver variables become instrument observations;
- units, coordinates, timing and data layout;
- how a fresh worker reconstructs or continues the numerical state;
- which lower- and higher-fidelity models can receive the same intervention;
- one scientific question whose answer changes with the measurements.

## Battery electrochemistry through PyBaMM

`labs/pybamm-battery` registers SPM, SPMe and DFN as three laboratories with the same current-step
interface. PyBaMM supplies the electrochemical equations, parameter library, discretisation and
solver. Synthetic Lab supplies persistent protocols, workers, branches, selected readouts and
time-series storage.

The adapter reconstructs a simulation by replaying the committed current history. This gives
process-independent continuation without serialising solver internals. It is suitable for short and
medium protocols. Long cycling studies should add a solver-native restart representation stored as
an external experiment object while preserving the same public operations.

A current step records actual elapsed time when a voltage cut-off ends it early. Later rest or charge
steps continue from that endpoint. Endpoint reads are cached solver outputs with no acquisition delay;
a device-specific sensor model can later add bandwidth, calibration and noise without changing the
electrochemistry.

## Full-wave photonics through Meep

`labs/meep-photonics` represents one fabricated photonic-crystal waveguide cavity. The public design
sets hole radius and defect spacing. Fabrication draws one hidden geometric offset, which remains the
same sample for every later measurement and experimental branch.

Broadband transmission uses a straight-waveguide reference and a cavity run with the same source,
cell, monitor and resolution. Meep supplies the time-domain Maxwell solution. Synthetic Lab converts
the flux ratio into a wavelength-indexed spectrometer observation, extracts a central-band resonance,
and stores a resonant two-dimensional field map outside the operation database.

This package establishes three boundaries that future photonics solvers should share:

- material and geometry are stated in physical units;
- power is normalized against an explicit optical reference;
- numerical field variables become finite-time instrument observations rather than raw solver state.

The present model is two-dimensional, lossless and nondispersive. The next photonics step is to give
transfer-matrix and RCWA packages the same material, geometry, illumination and detector description,
then compare their spectra with Meep on structures all three methods can represent. Measured index,
SEM geometry and spectrometer response can subsequently turn the same operations into a named-device
model.

## Expansion

A new solver belongs in the repository when it exercises a materially different scientific
structure. Strong successors are Cantera for reacting systems, FEniCS or OpenFOAM for spatial
transport, OpenMM or LAMMPS for molecular systems, and QuTiP for quantum control. Each should expose
a persistent experimental object and at least one intervention whose scientific conclusion depends
on the resulting observations.
