"""Persistent lithium-ion experiments executed by PyBaMM."""

from __future__ import annotations

import math

import numpy as np
import pybamm

from synthetic_lab.model import Model, Parameter, reading
from synthetic_lab.research import ResearchContract

_PARAMETER_SET = "Chen2020"
_OUTPUT_UNITS = {
    "time_s": "s",
    "current_a": "A",
    "terminal_voltage_v": "V",
    "cell_temperature_k": "K",
    "discharge_capacity_ah": "A.h",
    "state_of_charge": None,
}


def _finite_series(values, name):
    result = [float(value) for value in values.reshape(-1)]
    if not result or any(not math.isfinite(value) for value in result):
        raise ValueError(f"PyBaMM returned a non-finite or empty {name} series")
    return result


class _OperationCallbacks(pybamm.callbacks.Callback):
    """A partial experiment after a solver failure cannot complete an operation."""

    def on_experiment_error(self, logs):
        raise logs["error"]

    def on_experiment_infeasible_event(self, logs):
        raise pybamm.SolverError(f"Model stopped outside the cycler limits: {logs['termination']}")


def _contract(model_family, represented_physics):
    return ResearchContract(
        domains=(
            "electrochemical energy storage",
            "battery modelling",
            "experiment design",
        ),
        phenomena=tuple(represented_physics),
        questions=(
            "How do voltage, temperature and state of charge evolve under a held-out current protocol?",
            "Which pulse and rest sequence separates ohmic, kinetic and transport effects?",
            "When do SPM, SPMe and DFN predictions diverge enough to change an experiment decision?",
            "Which measurements are needed before a lower-fidelity model can be trusted for a new duty cycle?",
        ),
        observables={
            "terminal_voltage": {
                "unit": "V",
                "description": "Cell terminal voltage predicted by the selected PyBaMM model.",
            },
            "current": {
                "unit": "A",
                "description": "Applied cell current; positive current discharges the cell.",
            },
            "cell_temperature": {
                "unit": "K",
                "description": "Volume-averaged cell temperature from the lumped thermal model.",
            },
            "state_of_charge": {
                "unit": None,
                "description": "Unclipped coulomb-count estimate: initial SOC minus net discharge capacity divided by nominal capacity; not a direct sensor reading.",
            },
            "discharge_capacity": {
                "unit": "A.h",
                "description": "Net discharge capacity integrated by PyBaMM.",
            },
            "battery_trace": {
                "unit": None,
                "description": "Time-resolved current, voltage, temperature, capacity and state-of-charge series.",
            },
            "solver_termination": {
                "unit": None,
                "description": "Initial state, completed duration or voltage cut-off at the solved endpoint.",
            },
        },
        latent_variables={
            "particle_concentration_fields": {
                "unit": "mol/m3",
                "description": "Lithium concentration fields represented by the selected electrochemical model.",
            },
            "electrolyte_state": {
                "unit": None,
                "description": "Electrolyte concentration and potential where represented by the model family.",
            },
            "reaction_overpotentials": {
                "unit": "V",
                "description": "Electrode kinetic and transport overpotentials internal to the solver.",
            },
        },
        interventions=("step",),
        invariants=(
            "Simulation time is monotone and equals the completed PyBaMM experiment duration.",
            "Net discharge capacity is the time integral of current, including negative charging current.",
            "Each current segment ends at its requested duration or the parameter set's directional voltage cut-off.",
            "The same parameter set and current history are replayed when a persisted experiment continues.",
        ),
        validity_conditions=(
            "The Chen2020 lithium-ion parameter set represents the cell being studied closely enough for the question.",
            "The cell is represented by a one-dimensional through-thickness porous-electrode geometry.",
            "The lumped thermal option is adequate for the imposed current and cooling conditions.",
        ),
        limitations=(
            "The package does not include degradation, plating, cracking or three-dimensional current-collector effects.",
            "Model state is reconstructed from the committed current protocol when a later operation runs.",
            "Generic parameter values are not a calibration of a named physical cell.",
            "Reads expose noiseless cached solver outputs with no acquisition delay; no detector response is modelled.",
            "Coulomb-count SOC uses nominal capacity and can leave zero to one; it is not clipped or a concentration field.",
        ),
        failure_conditions=(
            "A numerical failure or a model event outside the cycler voltage limits prevents the operation from completing.",
            "The requested protocol lies outside the numerical or parameter range of the selected model.",
            "A scientific conclusion depends on effects omitted by the selected SPM, SPMe or DFN representation.",
        ),
        fidelity="reduced-order",
        action_semantics={
            "step": {
                "kind": "intervention",
                "description": "Apply current until the requested duration or directional voltage cut-off. Replay prior segments unchanged; record actual elapsed time.",
            },
            "read": {
                "kind": "measurement",
                "description": "Read cached electrical, thermal or derived state outputs without advancing time, including the initial open-circuit state.",
            },
            "trace": {
                "kind": "measurement",
                "description": "Return the time-resolved solver output for the complete committed protocol.",
            },
        },
        reference_methods=(
            "equivalent-circuit pulse analysis",
            "single-particle model",
            "single-particle model with electrolyte",
            "Doyle-Fuller-Newman porous-electrode model",
        ),
        physical_counterpart="A lithium-ion cell connected to a programmable cycler and temperature sensor",
        metadata={
            "solver_backend": "PyBaMM",
            "solver_model": model_family,
            "parameter_set": _PARAMETER_SET,
            "observation_model": "noiseless solver outputs; instantaneous cached reads",
            "continuation": "replay unchanged current segments with their voltage terminations",
            "represented_physics": list(represented_physics),
            "upstream_project": "pybamm-team/PyBaMM",
        },
    )


class PyBaMMBatteryLab(Model):
    """Shared implementation for one PyBaMM lithium-ion model family."""

    version = "2"
    model_family = ""
    represented_physics = ()
    defaults = {
        "initial_soc": 0.8,
        "ambient_temperature": 298.15,
        "sample_period": 5.0,
    }
    parameters = {
        "initial_soc": Parameter(None, 0.05, 1.0),
        "ambient_temperature": Parameter("K", 273.15, 333.15),
        "sample_period": Parameter("s", 0.1, 300.0),
    }
    actions = {
        "step": {
            "current": Parameter("A", -10.0, 10.0),
            "seconds": Parameter("s", 0.1, 14400.0),
        },
        "read": {"instrument": Parameter(choices=("electrical", "thermal", "state", "summary"))},
        "trace": {},
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.research = _contract(self.model_family, self.represented_physics)

    def initial(self, rng):
        del rng
        return {
            "time_s": 0.0,
            "protocol": [],
            "endpoint": None,
            "trajectory": None,
            "termination": None,
            "solve_count": 0,
        }

    def advance(self, state, seconds):
        if seconds > 0:
            self._append_step(state, 0.0, seconds)
            self._solve(state)

    def _model(self):
        options = {"thermal": "lumped"}
        factories = {
            "SPM": pybamm.lithium_ion.SPM,
            "SPMe": pybamm.lithium_ion.SPMe,
            "DFN": pybamm.lithium_ion.DFN,
        }
        return factories[self.model_family](options=options)

    def _parameters(self):
        values = pybamm.ParameterValues(_PARAMETER_SET)
        values.update(
            {
                "Ambient temperature [K]": self.config["ambient_temperature"],
                "Initial temperature [K]": self.config["ambient_temperature"],
            }
        )
        return values

    def _append_step(self, state, current, seconds):
        # Preserve operation boundaries, including a prior segment's cut-off.
        state["protocol"].append({"current_a": float(current), "seconds": float(seconds)})

    def _experiment(self, protocol, parameters):
        steps = []
        sample_period = self.config["sample_period"]
        for segment in protocol:
            duration = segment["seconds"]
            current = segment["current_a"]
            termination = None
            if current != 0:
                bound = "Lower" if current > 0 else "Upper"
                termination = f"{parameters[f'{bound} voltage cut-off [V]']} V"
            steps.append(
                pybamm.step.current(
                    current,
                    duration=duration,
                    period=min(sample_period, duration),
                    temperature=self.config["ambient_temperature"],
                    termination=termination,
                    skip_ok=False,
                )
            )
        return pybamm.Experiment(steps, temperature=self.config["ambient_temperature"])

    def _solve(self, state):
        parameters = self._parameters()
        simulation = pybamm.Simulation(
            self._model(),
            parameter_values=parameters,
            experiment=self._experiment(state["protocol"], parameters),
        )
        solution = simulation.solve(
            initial_soc=self.config["initial_soc"],
            calc_esoh=False,
            showprogress=False,
            callbacks=_OperationCallbacks(),
        )
        self._store_solution(state, solution, parameters)

    def _initial_solution(self, state):
        # Solve the initial algebraic constraints without integrating a time interval.
        parameters = self._parameters()
        parameters.update({"Current function [A]": 0.0})
        simulation = pybamm.Simulation(self._model(), parameter_values=parameters)
        simulation.build(initial_soc=self.config["initial_soc"])
        model = simulation.built_model
        simulation.solver.set_up(model)
        initial_state = simulation.solver.calculate_consistent_state(model)[0]
        solution = pybamm.Solution(np.array([0.0]), initial_state, model, {})
        self._store_solution(state, solution, parameters)
        state["termination"] = "initial state"

    def _store_solution(self, state, solution, parameters):
        time_s = _finite_series(solution.t, "time")
        current_a = _finite_series(solution["Current [A]"].entries, "current")
        voltage_v = _finite_series(solution["Terminal voltage [V]"].entries, "voltage")
        temperature_k = _finite_series(
            solution["Volume-averaged cell temperature [K]"].entries,
            "temperature",
        )
        capacity_ah = _finite_series(
            solution["Discharge capacity [A.h]"].entries,
            "discharge capacity",
        )
        if any(
            length != len(time_s)
            for length in (
                len(current_a),
                len(voltage_v),
                len(temperature_k),
                len(capacity_ah),
            )
        ):
            raise ValueError("PyBaMM outputs do not share the same time axis")

        nominal_capacity = float(parameters["Nominal cell capacity [A.h]"])
        state_of_charge = [
            self.config["initial_soc"] - capacity / nominal_capacity for capacity in capacity_ah
        ]
        state["time_s"] = time_s[-1]
        state["termination"] = str(solution.termination)
        state["endpoint"] = {
            "current_a": current_a[-1],
            "terminal_voltage_v": voltage_v[-1],
            "cell_temperature_k": temperature_k[-1],
            "discharge_capacity_ah": capacity_ah[-1],
            "state_of_charge": state_of_charge[-1],
        }
        state["trajectory"] = {
            "time_s": time_s,
            "current_a": current_a,
            "terminal_voltage_v": voltage_v,
            "cell_temperature_k": temperature_k,
            "discharge_capacity_ah": capacity_ah,
            "state_of_charge": state_of_charge,
        }
        state["solve_count"] += 1

    def _ensure_solution(self, state):
        if state["endpoint"] is None:
            self._initial_solution(state)

    def _endpoint_observations(self, state, instrument):
        endpoint = state["endpoint"]
        observations = {}
        if instrument in ("electrical", "summary"):
            observations.update(
                {
                    "terminal_voltage": reading(endpoint["terminal_voltage_v"], "V"),
                    "current": reading(endpoint["current_a"], "A"),
                }
            )
        if instrument in ("thermal", "summary"):
            observations["cell_temperature"] = reading(endpoint["cell_temperature_k"], "K")
        if instrument in ("state", "summary"):
            observations.update(
                {
                    "state_of_charge": reading(
                        endpoint["state_of_charge"], None, method="nominal-capacity coulomb count"
                    ),
                    "discharge_capacity": reading(endpoint["discharge_capacity_ah"], "A.h"),
                }
            )
        observations["solver_termination"] = {
            "value": state["termination"],
            "unit": None,
        }
        return observations

    def perform(self, state, rng, action, params):
        del rng
        if action == "step":
            self._append_step(state, params["current"], params["seconds"])
            self._solve(state)
            return self._endpoint_observations(state, "summary")
        if action == "read":
            self._ensure_solution(state)
            return self._endpoint_observations(state, params["instrument"])
        if action == "trace":
            self._ensure_solution(state)
            sample_count = len(state["trajectory"]["time_s"])
            return {
                "battery_trace": {
                    "value": state["trajectory"],
                    "unit": None,
                    "shape": [sample_count],
                    "axes": ["sample"],
                    "fields": dict(_OUTPUT_UNITS),
                    "solver_model": self.model_family,
                    "parameter_set": _PARAMETER_SET,
                    "termination": state["termination"],
                }
            }
        return {}

    def visible(self, state):
        endpoint = state["endpoint"] or {}
        return {
            "solver_backend": "PyBaMM",
            "solver_model": self.model_family,
            "parameter_set": _PARAMETER_SET,
            "elapsed_s": state["time_s"],
            "applied_current_a": endpoint.get("current_a", 0.0),
            "protocol_segments": len(state["protocol"]),
            "solver_runs": state["solve_count"],
        }


class SPMBatteryLab(PyBaMMBatteryLab):
    name = "pybamm-battery-spm"
    model_family = "SPM"
    represented_physics = (
        "solid-particle diffusion",
        "interfacial electrochemical kinetics",
        "lumped cell temperature",
    )
    description = "PyBaMM single-particle lithium-ion laboratory for fast protocol exploration."


class SPMeBatteryLab(PyBaMMBatteryLab):
    name = "pybamm-battery-spme"
    model_family = "SPMe"
    represented_physics = (
        "solid-particle diffusion",
        "electrolyte concentration and potential",
        "interfacial electrochemical kinetics",
        "lumped cell temperature",
    )
    description = (
        "PyBaMM single-particle-with-electrolyte laboratory for transport-aware experiments."
    )


class DFNBatteryLab(PyBaMMBatteryLab):
    name = "pybamm-battery-dfn"
    model_family = "DFN"
    represented_physics = (
        "porous-electrode transport",
        "solid-particle diffusion",
        "electrolyte concentration and potential",
        "interfacial electrochemical kinetics",
        "lumped cell temperature",
    )
    description = "PyBaMM Doyle-Fuller-Newman laboratory for porous-electrode protocol studies."
