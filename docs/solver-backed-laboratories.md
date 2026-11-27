# Solver-backed laboratories

Synthetic Lab does not reimplement mature numerical science. A domain package owns the translation
between persistent experimental operations and an established solver. The common runtime retains
session identity, simulation time, branching, queued execution, observations and large data; the
solver retains its equations, discretisation and numerical methods.

```text
researcher or agent
        |
        v
Synthetic Lab operation
        |
        v
domain package adapter
        |
        +-- PyBaMM / Cantera / OpenFOAM / Meep / OpenMM / other solver
        |
        v
selected physical variables
        |
        v
instrument-like observations and external data
```

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

A second solver should be added only when it exercises a materially different scientific structure.
Strong next candidates are wave optics through Meep or RCWA, reacting systems through Cantera, and
continuum transport through FEniCS or OpenFOAM.
