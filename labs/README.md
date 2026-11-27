# Domain laboratory packages

Domain laboratories are independently installable packages discovered through the
`synthetic_lab.models` entry point. They share persistent sessions, branching, units, observations
and research contracts without moving domain equations or dependencies into the core runtime.

| Package | Laboratories | Scientific role |
|---|---|---|
| [`meep-photonics`](meep-photonics) | `meep-photonic-cavity` | Full-wave cavity design, fabrication variation, transmission spectroscopy and field imaging |
| [`pybamm-battery`](pybamm-battery) | `pybamm-battery-spm`, `pybamm-battery-spme`, `pybamm-battery-dfn` | Run one battery protocol across established single-particle and porous-electrode solvers |
| [`optical-metrology`](optical-metrology) | `thin-film`, `fluorescence-microscopy` | Fabrication endpoint selection and dose-limited scientific imaging |
| [`spectroscopic-bioprocess`](spectroscopic-bioprocess) | `spectroscopic-bioreactor` | Fed-batch growth, optical induction and complementary process sensing |
| [`tank example`](../examples/tank-package) | `fluid-tank` | Transient fluid balance and outlet-conductance estimation |

The Meep package represents a fabricated photonic-crystal cavity as a persistent sample. Meep solves
the time-domain Maxwell equations; Synthetic Lab owns design actions, hidden fabrication variation,
measurement time, normalized spectra, branches, workers and external field-map storage.

The PyBaMM package runs one current protocol through SPM, SPMe and DFN. Synthetic Lab owns the
experiment operations, history, workers and observations; PyBaMM supplies electrochemistry,
discretisation and numerical integration.

The optical-metrology package also registers `synthetic-thin-film-endpoint` and
`synthetic-microscopy-focus` with Verifiable Agent Gym. These tasks score the final physical
endpoint and photon-dose trade rather than a textual description of the experiment.

A maintained package should provide:

- one consequential experimental question rather than a catalogue of disconnected controls;
- persistent hidden state, finite-time actions and realistic measurement formation;
- a complete machine-readable research contract;
- a branch or held-out-condition experiment using public observations;
- physical relations exercised independently from the example policy;
- a path from transparent mechanism to measured calibration and prediction on new conditions.

Install pip-based packages beside the core:

```sh
python -m pip install -e .
python -m pip install -e labs/pybamm-battery
python -m pip install -e labs/optical-metrology
python -m pip install -e labs/spectroscopic-bioprocess
python -m pip install -e examples/tank-package
```

Meep uses a conda-forge environment:

```sh
conda env create -f labs/meep-photonics/environment.yml
conda activate synthetic-lab-meep
python -m pip install -e . -e labs/meep-photonics
```

Large numerical dependencies, measured assets and specialized solvers stay within their domain
package. Real instrument operations remain delegated to IOP; the laboratory package owns simulated
state and observation generation. See [solver-backed laboratories](../docs/solver-backed-laboratories.md)
for the adapter boundary.
