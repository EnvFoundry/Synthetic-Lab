"""An independently packaged fluid experiment with a linear outlet resistance."""

import math

from synthetic_lab.model import Model, Parameter, reading
from synthetic_lab.research import ResearchContract


class Tank(Model):
    name = "fluid-tank"
    description = "Infer a laminar outlet conductance by choosing inflow and measuring level."
    actions = {
        "pump": {"flow": Parameter("m3/s", 0, 0.0002)},
        "wait": {"seconds": Parameter("s", 0, 3600)},
        "read": {},
    }
    defaults = {"area": 0.05, "conductance": 0.0004}
    parameters = {"area": Parameter("m2", 0.01, 1), "conductance": Parameter("m2/s", 0.0002, 0.001)}
    research = ResearchContract(
        domains=("fluid mechanics", "process control"),
        phenomena=("volume balance", "linear hydraulic resistance"),
        questions=("Can transient level measurements identify an unknown outlet conductance?",),
        observables={"level": {"unit": "m", "description": "Noisy liquid height."}},
        latent_variables={
            "conductance": {"unit": "m2/s", "description": "Specimen-specific outlet conductance."},
            "level": {"unit": "m", "description": "Actual liquid height before sensor noise."},
        },
        interventions=("pump",),
        invariants=("Initial volume plus inflow equals stored volume plus outflow.",),
        validity_conditions=("Uniform cross-section, incompressible liquid and a linear outlet.",),
        limitations=("No turbulence, overflow, evaporation or pump lag.",),
        failure_conditions=("A nonlinear outlet cannot be identified by this linear model.",),
        fidelity="analytical",
        action_semantics={
            "pump": {"kind": "control", "description": "Set inlet volume flow."},
            "wait": {"kind": "wait", "description": "Continue inflow and drainage."},
            "read": {"kind": "measurement", "description": "Measure level after 0.1 seconds."},
        },
        reference_methods=("steady-state conductance estimate", "transient exponential fit"),
        physical_counterpart="A constant-area tank with a pump and resistive drain",
    )

    def initial(self, rng):
        return {
            "time_s": 0.0,
            "flow": 0.0,
            "level": 0.1,
            "conductance": self.config["conductance"] * rng.uniform(0.9, 1.1),
            "input_volume": 0.0,
            "output_volume": 0.0,
        }

    def advance(self, state, seconds):
        area = self.config["area"]
        conductance = state["conductance"]
        before = state["level"]
        equilibrium = state["flow"] / conductance
        state["level"] = equilibrium + (before - equilibrium) * math.exp(
            -conductance * seconds / area
        )
        incoming = state["flow"] * seconds
        state["input_volume"] += incoming
        state["output_volume"] += incoming - area * (state["level"] - before)
        state["time_s"] += seconds

    def perform(self, state, rng, action, params):
        if action == "pump":
            state["flow"] = params["flow"]
            self.advance(state, 0.1)
        elif action == "wait":
            self.advance(state, params["seconds"])
        elif action == "read":
            self.advance(state, 0.1)
            return {"level": reading(state["level"] + rng.gauss(0, 0.0005), "m", 0.0005)}
        return {}

    def visible(self, state):
        return {"pump_flow_m3_per_s": state["flow"]}
