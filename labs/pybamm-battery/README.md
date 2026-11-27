# PyBaMM battery laboratories

This package connects Synthetic Lab to [PyBaMM](https://github.com/pybamm-team/PyBaMM). It does not
reimplement electrochemical solvers. The package translates persistent experiment operations into
PyBaMM experiments and converts selected solver variables into instrument-like observations.

It contributes three laboratories sharing the same controls and parameter set:

| Laboratory | PyBaMM model | Main represented physics |
|---|---|---|
| `pybamm-battery-spm` | SPM | solid-particle diffusion and kinetics |
| `pybamm-battery-spme` | SPMe | SPM physics plus electrolyte transport |
| `pybamm-battery-dfn` | DFN | porous-electrode transport, particles, electrolyte and kinetics |

All three use PyBaMM's `Chen2020` LG M50 parameter set, lumped thermal option and default IDAKLU
solver and mesh. The published parameterisation belongs to PyBaMM; this package has no measurements
from a particular cell in the user's laboratory. A session stores its constant-current protocol,
endpoint outputs and selected time series. A later worker reconstructs the solver state by replaying
the committed segments, so the experiment can resume in a fresh process.

## Install

```sh
python -m pip install -e .
python -m pip install -e labs/pybamm-battery
```

PyBaMM is installed only in the battery worker environment. A client that submits operations to an
existing session needs only the Synthetic Lab core.

## Run

```python
from synthetic_lab import Lab

with Lab("runs/battery.sqlite") as lab:
    cell = lab.create(
        "pybamm-battery-spme",
        config={"initial_soc": 0.8, "ambient_temperature": 298.15, "sample_period": 5},
    )
    endpoint = cell.act("step", current=5.0, seconds=600.0)
    trace = cell.act("trace")
    print(endpoint["observations"]["terminal_voltage"])
    print(trace["observations"]["battery_trace"]["value"])
```

## Operations and observations

| Operation | Time and output |
|---|---|
| `step(current, seconds)` | Positive current discharges, negative current charges, zero current rests. Ends at the requested duration or the directional voltage cut-off, whichever occurs first |
| `read(instrument="electrical")` | Cached terminal voltage and current at the latest endpoint |
| `read(instrument="thermal")` | Cached volume-averaged cell temperature |
| `read(instrument="state")` | Integrated net discharge capacity and nominal-capacity SOC estimate |
| `read(instrument="summary")` | All endpoint outputs |
| `trace()` | Time, current, voltage, temperature, net capacity and SOC estimate over the committed protocol |

The `Chen2020` cycler limits are **2.5 V on discharge and 4.2 V on charge**. A cut-off completes the
operation with a shorter interval and an explicit `solver_termination`. `end_s - start_s` is the
actual elapsed duration; the requested `seconds` remains in the operation record. Rest or reverse
current can follow a cut-off, including after reopening or branching a session. A current that
already exceeds its voltage bound cannot begin. A numerical failure leaves the prior committed
state intact instead of returning an earlier protocol segment as a successful new operation.

`read` and `trace` do not advance time. The first read solves the open-circuit initial algebraic
constraints at **t = 0**, with no hidden rest segment. Outputs are noiseless solver predictions;
sensor bandwidth, measurement noise, acquisition delay and wall-clock evolution are not represented.
Different seeds therefore do not generate different cells in this package.

With positive discharge current, net capacity is

\[
Q_d(t)=\frac{1}{3600}\int_0^t I(\tau)\,d\tau,
\qquad \widehat{SOC}(t)=SOC_0-\frac{Q_d(t)}{Q_{\rm nominal}}.
\]

Charging reduces `discharge_capacity`; it is not cumulative absolute throughput. The SOC output is
a derived estimate, not a direct measurement or electrode concentration. It is **not clipped** to
0–1: the nominal capacity need not equal the capacity implied by the electrode parameterisation.

All trace fields share one time axis and retain both sides of current transitions. `sample_period`
controls requested output spacing, not the solver's internal time step. Large traces use the
external data store; unchanged reads reuse their object reference.

## Continuation and comparison

Each operation retains its own segment even when adjacent currents are equal. Replay uses the same
durations and voltage events, preserving earlier output samples and any early cut-off. The sum of
requested durations can exceed elapsed experiment time. The stored protocol, model configuration
and PyBaMM implementation together determine the reconstructed electrochemical fields.

```sh
python examples/compare_pybamm_models.py
```

The comparison applies 5 A for 300 s followed by 300 s at zero current, from SOC 0.8 and 298.15 K.
It reports both actual durations and stops if a model cannot complete the common programme. Its
wall time includes creation and both operations, including replay during the second operation.
DFN is a comparison model, not measured ground truth. Mesh refinement and tighter solver tolerances
are needed before interpreting differences near numerical resolution.

For many equal-length submitted segments, replay solves a growing prefix on every operation;
total integration work grows approximately quadratically with segment count. Long cycling needs
a solver-native restart state containing the electrochemical and thermal fields. That representation
belongs in this package and can use the existing external data store; it is not implemented here.

Model revision 2 changes initial reads, cut-offs, segment boundaries and SOC interpretation. Sessions
created with the original PR implementation remain readable, but continuation requires that original
adapter. Create a new session to use the corrected physical history.

## Scope

This is a solver-backed reference environment, not a calibrated twin of a named cell. Its scientific
value is the shared experiment surface across SPM, SPMe and DFN: the same current protocol can be run
at several physical fidelities, and a researcher can measure where a cheaper model changes an
experimental decision. Device-specific work should supply measured parameters, thermal boundary
conditions and held-out cycling data in a separate package.

PyBaMM is distributed under the BSD 3-Clause licence. This package depends on PyBaMM without
vendoring its source. See its [experiment termination documentation](https://docs.pybamm.org/en/stable/source/api/experiment/experiment.html)
and [Chen2020 parameter documentation](https://docs.pybamm.org/en/latest/source/api/parameters/parameter_sets.html#chen2020).
