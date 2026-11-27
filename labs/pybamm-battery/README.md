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

All three use the `Chen2020` parameter set and lumped thermal option. A session stores its complete
constant-current protocol, endpoint observations and selected time series. A later worker reconstructs
the solver state by replaying that committed protocol, so the experiment can resume in a fresh process
without serialising PyBaMM internals.

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

Positive current discharges the cell; negative current charges it. A zero-current step is a rest.
The endpoint action returns voltage, current, average temperature, net discharge capacity and state
of charge. `trace` returns the same variables over time and is automatically moved to the external
experiment-data store when it crosses the configured size threshold.

## Scope

This is a solver-backed reference environment, not a calibrated twin of a named cell. Its scientific
value is the shared experiment surface across SPM, SPMe and DFN: the same current protocol can be run
at several physical fidelities, and a researcher can measure where a cheaper model changes an
experimental decision. Device-specific work should supply measured parameters, thermal boundary
conditions and held-out cycling data in a separate package.

PyBaMM is distributed under the BSD 3-Clause licence. This package depends on PyBaMM without
vendoring its source.
