"""A task factory for EnvFoundry Verifiable Agent Gym."""

from agent_gym.contracts import Task, Tool, Verdict, number, object_schema

from ..models.thermal import ThermalBench
from ..runtime import Lab


class ThermalExperiment:
    def __init__(self, seed, resistance):
        self.lab = Lab(":memory:")
        self.session = self.lab.create(
            "thermal", seed=seed, config={"thermal_resistance": resistance, "variation": 0.0}
        )
        self.tools = tuple(
            Tool(
                name,
                f"Thermal bench operation {name}. Values use SI units.",
                object_schema({key: p.describe() for key, p in params.items()}, list(params)),
            )
            for name, params in ThermalBench.actions.items()
            if name != "clamp"
        )

    def call(self, name, arguments):
        if name not in {tool.name for tool in self.tools}:
            raise ValueError("This task permits supply, connect, wait and read")
        return self.session.act(name, **arguments)

    def close(self):
        self.lab.close()


def make(spec):
    if spec.version != 1:
        raise ValueError("synthetic-thermal supports task version 1")
    rng = spec.rng()
    resistance = rng.uniform(6, 14)
    environment = ThermalExperiment(rng.randrange(2**63), resistance)

    def verify(answer):
        try:
            if not isinstance(answer, dict) or set(answer) != {"thermal_resistance_k_per_w"}:
                raise ValueError("Submit thermal_resistance_k_per_w")
            estimate = number(answer["thermal_resistance_k_per_w"], "thermal_resistance_k_per_w")
            error = abs(estimate - resistance)
            passed = error <= 0.5
            return Verdict(
                passed,
                max(0.0, 1 - error / 2),
                "Thermal resistance compared to the configured specimen",
                {"absolute_error_k_per_w": error},
            )
        except ValueError as exc:
            return Verdict(False, 0, str(exc))

    prompt = (
        "Estimate this heater's thermal resistance in K/W. You can connect an ambient "
        "thermometer and voltage/current metering, choose supply voltages, wait and read. "
        "Allow the system to settle and account for thermometer offset. Submit "
        "{thermal_resistance_k_per_w: number}; tolerance is 0.5 K/W. "
        "All readings are simulated. Each wait may span at most 3600 seconds."
    )
    return Task(spec, prompt, environment, verify, max_actions=24)
