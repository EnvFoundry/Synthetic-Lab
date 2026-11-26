# Research contract

A laboratory catalogue should describe more than callable controls. A researcher or agent must
also know what can be learned, which quantities are hidden, which observations distinguish
competing explanations, and where the model stops being useful. `ResearchContract` makes that
scientific surface discoverable beside the action schema.

## Contract fields

| Field | Meaning |
|---|---|
| `domains` | Scientific and engineering fields served by the laboratory |
| `phenomena` | Mechanisms represented in the state transition and observation models |
| `questions` | Concrete questions an experiment in this laboratory can resolve |
| `observables` | Named measured quantities, units and physical meaning |
| `latent_variables` | Hidden quantities that govern future observations but are not exposed to an agent |
| `interventions` | Actions that deliberately change the specimen, apparatus or process |
| `invariants` | Conservation laws, bounds or relationships that implementations must preserve |
| `failure_conditions` | Physical, numerical or informational conditions that invalidate a run |
| `validity` | Fidelity class, operating assumptions and explicit limitations |
| `action_semantics` | A complete map from every action to `configure`, `control`, `intervention`, `measurement` or `wait` |
| `reference_methods` | Domain methods that provide meaningful baselines or parameter estimates |
| `physical_counterpart` | The class of apparatus the model is intended to represent, not a claim of calibration |

`Model.describe()` validates the contract and returns it under `research_contract`. Python, CLI,
JSON-lines and MCP catalogue clients therefore see the same scientific scope. The contract is
class-level metadata: it describes the model family and never exposes the realized hidden state
of a specimen.

## Fidelity ladder

The contract uses five broad fidelity classes.

1. **Analytical** — closed-form or elementary numerical relations used to expose a mechanism.
2. **Reduced-order** — coupled dynamics that retain task-relevant state but omit substantial
   spatial, chemical or multiscale detail.
3. **Surrogate** — a learned approximation tied to a stated training distribution.
4. **Empirical** — a model calibrated directly against measurements from a defined population or
   device class.
5. **Hybrid** — mechanistic state evolution combined with learned or empirical components.

Fidelity is not a quality score. A transparent reduced-order model can be the right environment
for causal experiment design, while a high-resolution solver can be useless when its parameters
are not identifiable from available observations.

A **digital twin** requires more than the `empirical` label. It needs a named physical counterpart,
bidirectional updates or a defined synchronization procedure, calibration data, an operating
range, uncertainty, and predictive results on conditions not used for fitting.

## Acceptance criteria for a laboratory

A maintained laboratory should include:

- one executable question with a nontrivial experimental choice;
- explicit state, time, controls, measurements and hidden variables;
- units, noise, finite range and measurement duration where they matter;
- at least one governing invariant or limiting case checked in tests;
- a failure condition that changes what the experimenter may conclude;
- a reference method using only public observations;
- a branch or held-out intervention that tests a prediction rather than replaying fitted data;
- documentation separating simulated, fitted and measured quantities.

A large catalogue of disconnected toy functions does not satisfy this standard. New domains
should normally arrive as independently versioned packages. The core owns the contract and
persistent experiment semantics; domain packages own solvers, datasets and specialized
dependencies.

## Example

```python
from synthetic_lab import ResearchContract

research = ResearchContract(
    domains=("fluid mechanics",),
    phenomena=("volume balance",),
    questions=("Can a held-out inflow identify the outlet law?",),
    observables={"level": {"unit": "m", "description": "Measured liquid height."}},
    latent_variables={
        "conductance": {"unit": "m2/s", "description": "Outlet conductance."}
    },
    interventions=("pump",),
    invariants=("Volume change equals inflow minus outflow.",),
    failure_conditions=("The assumed laminar outlet law ceases to apply.",),
    validity_conditions=("Uniform cross-section and linear outlet resistance.",),
    limitations=("No turbulence or overflow.",),
    fidelity="analytical",
    action_semantics={
        "pump": {"kind": "control", "description": "Set inflow."},
        "wait": {"kind": "wait", "description": "Advance the experiment."},
        "read": {"kind": "measurement", "description": "Measure level."},
    },
)
```
