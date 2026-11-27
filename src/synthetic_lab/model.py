"""The domain boundary. Implementations own physics; the runtime owns persistence."""

import random
from dataclasses import dataclass
from typing import ClassVar

from .quantities import quantity
from .research import ResearchContract


@dataclass(frozen=True)
class Parameter:
    unit: str | None = None
    minimum: float = 0.0
    maximum: float = 1.0
    choices: tuple[str, ...] = ()

    def parse(self, value):
        if self.choices:
            if not isinstance(value, str) or value not in self.choices:
                raise ValueError(f"Expected one of {self.choices}")
            return value
        result = quantity(value, self.unit)
        if not self.minimum <= result <= self.maximum:
            raise ValueError(f"Value must be in [{self.minimum}, {self.maximum}] {self.unit or ''}")
        return result

    def describe(self):
        if self.choices:
            return {"type": "string", "enum": list(self.choices)}
        return {
            "type": "number",
            "unit": self.unit,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

    @classmethod
    def from_description(cls, description):
        if description["type"] == "string":
            return cls(choices=tuple(description["enum"]))
        return cls(description["unit"], description["minimum"], description["maximum"])


def arguments(values, specification):
    if not isinstance(values, dict) or values.keys() != specification.keys():
        raise ValueError(f"Expected parameters {sorted(specification)}")
    return {key: parameter.parse(values[key]) for key, parameter in specification.items()}


def reading(value, unit, noise_std=0.0, **metadata):
    return {"value": value, "unit": unit, "noise_std": noise_std, **metadata}


class Model:
    name: ClassVar[str]
    version: ClassVar[str] = "1"
    description: ClassVar[str]
    actions: ClassVar[dict[str, dict[str, Parameter]]]
    defaults: ClassVar[dict] = {}
    parameters: ClassVar[dict[str, Parameter]] = {}
    research: ClassVar[ResearchContract | None] = None

    def __init__(self, config=None):
        config = {} if config is None else config
        if not isinstance(config, dict) or not config.keys() <= self.defaults.keys():
            raise ValueError(f"Configuration keys must be among {sorted(self.defaults)}")
        self.config = dict(self.defaults)
        for key, value in config.items():
            self.config[key] = self.parameters[key].parse(value)

    def initial(self, rng: random.Random):
        raise NotImplementedError

    def advance(self, state, seconds):
        raise NotImplementedError

    def perform(self, state, rng, action, params):
        raise NotImplementedError

    def visible(self, state):
        raise NotImplementedError

    def describe(self):
        result = {
            "name": self.name,
            "model_version": self.version,
            "description": self.description,
            "source": "simulation",
            "validation": "analytical model; no device-specific empirical calibration",
            "capabilities": ["resume", "fork", "simulation_time", "operation_deduplication"],
            "actions": {
                name: {key: p.describe() for key, p in fields.items()}
                for name, fields in self.actions.items()
            },
        }
        if self.research is not None:
            result["research_contract"] = self.research.describe(self.actions)
            result["capabilities"].append("research_contract")
            result["validation"] = (
                "model scope, invariants and limits are declared in research_contract; "
                "no device-specific empirical calibration"
            )
        return result
