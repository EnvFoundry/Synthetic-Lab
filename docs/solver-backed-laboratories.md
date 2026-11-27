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

The first implementation is `labs/pybamm-battery`. It registers SPM, SPMe and DFN as three
laboratories with the same current-step interface. PyBaMM supplies the electrochemical equations,
parameter library, discretisation and solver. Synthetic Lab supplies persistent protocols, workers,
branches, selected readouts and time-series storage.

The current PyBaMM adapter reconstructs a simulation by replaying the committed current history.
This gives process-independent continuation without serialising solver internals. It is suitable for
short and medium protocols. Long cycling studies should add a solver-native restart representation
stored as an external experiment object, while preserving the same public operations.

The adapter must distinguish a requested duration from actual elapsed time. A physical termination
can complete a shorter operation, after which later interventions must start from that endpoint.
Replaying an earlier cut-off must not silently discard the new intervention. Adjacent operations
retain their boundaries so that a later call does not change previously reported observations.

Solver output and instrument response are separate scientific choices. The PyBaMM package exposes
noiseless endpoint predictions and trajectories; it declares zero acquisition time and a derived
coulomb-count SOC. A device-specific sensor model can add bandwidth, calibration and noise without
changing PyBaMM's electrochemistry. More elaborate equations alone do not establish agreement with
a real instrument.

A second solver should be added only when it exercises a materially different scientific structure.
The next priority is wave optics: represent one specimen, material dispersion, illumination and
detector geometry consistently across transfer-matrix, RCWA and Meep calculations. Compare the
same spectrum first, including power normalization and numerical convergence; then reuse it in
an adaptive measurement or inverse-design experiment. Reacting systems through Cantera and continuum
transport through FEniCS or OpenFOAM are later candidates.
