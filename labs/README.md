# Domain laboratory packages

Domain laboratories are independently installable packages discovered through the
`synthetic_lab.models` entry point. They share persistent sessions, branching, units, observations
and research contracts without moving domain equations or dependencies into the core runtime.

| Package | Laboratories | Scientific role |
|---|---|---|
| [`physicell-car-t`](physicell-car-t) | `physicell-car-t-spheroid` | Compare CAR receptor dwell-time designs through spatial infiltration, exhaustion and antigen escape in a three-dimensional solid-tumor spheroid |
| [`physicell-organoid`](physicell-organoid) | `physicell-tumor-organoid` | Compare tumor-organoid exposures under shared hidden response heterogeneity using PhysiCell and BioFVM |
| [`pybamm-battery`](pybamm-battery) | `pybamm-battery-spm`, `pybamm-battery-spme`, `pybamm-battery-dfn` | Run one battery protocol across established single-particle and porous-electrode solvers |
| [`optical-metrology`](optical-metrology) | `thin-film`, `fluorescence-microscopy` | Fabrication endpoint selection and dose-limited scientific imaging |
| [`spectroscopic-bioprocess`](spectroscopic-bioprocess) | `spectroscopic-bioreactor` | Fed-batch growth, optical induction and complementary process sensing |
| [`tank example`](../examples/tank-package) | `fluid-tank` | Transient fluid balance and outlet-conductance estimation |

The solver-backed packages preserve the solver's governing equations inside the domain environment.
Synthetic Lab owns experiment operations, history, workers, branches and observations. PyBaMM
supplies lithium-ion electrochemistry; PhysiCell and BioFVM supply multicellular mechanics, oxygen,
treatment transport and spatial immune-cell interactions.

The optical package also registers `synthetic-thin-film-endpoint` and
`synthetic-microscopy-focus` with Verifiable Agent Gym. These tasks score the final physical
endpoint and photon-dose trade rather than a textual description of the experiment.

A maintained package should provide:

- one consequential experimental question rather than a catalogue of disconnected controls;
- persistent hidden state, finite-time actions and realistic measurement formation;
- a complete machine-readable research contract;
- a branch or held-out-condition experiment using public observations;
- physical relations tested independently from the example policy;
- a path from transparent mechanism to measured calibration and prediction on new conditions.

Install packages beside the core:

```sh
python -m pip install -e .
python -m pip install -e labs/physicell-car-t
python -m pip install -e labs/physicell-organoid
python -m pip install -e labs/pybamm-battery
python -m pip install -e labs/optical-metrology
python -m pip install -e labs/spectroscopic-bioprocess
python -m pip install -e examples/tank-package
```

The PhysiCell packages additionally require their external executables; each package README contains
the pinned 1.14.2 build command. Large numerical dependencies, measured assets and specialized
solvers stay within their domain package. Real instrument operations remain delegated to IOP; the
laboratory package owns simulated state and observation generation. See
[solver-backed laboratories](../docs/solver-backed-laboratories.md) for the adapter boundary.
