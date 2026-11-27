# Domain laboratory packages

Domain laboratories are independently installable packages discovered through the
`synthetic_lab.models` entry point. They share persistent sessions, branching, units, observations
and research contracts without moving domain equations or dependencies into the core runtime.

| Package | Laboratories | Scientific role |
|---|---|---|
| [`optical-metrology`](optical-metrology) | `thin-film`, `fluorescence-microscopy` | Fabrication endpoint selection and dose-limited scientific imaging |
| [`spectroscopic-bioprocess`](spectroscopic-bioprocess) | `spectroscopic-bioreactor` | Fed-batch growth, optical induction and complementary process sensing |
| [`tank example`](../examples/tank-package) | `fluid-tank` | Transient fluid balance and outlet-conductance estimation |

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
python -m pip install -e labs/optical-metrology
python -m pip install -e labs/spectroscopic-bioprocess
python -m pip install -e examples/tank-package
```

Large numerical dependencies, measured assets and specialized solvers stay within their domain
package. Real instrument operations remain delegated to IOP; the laboratory package owns simulated
state and observation generation.
