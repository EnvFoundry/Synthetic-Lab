"""Scientific intent and validity exposed beside a laboratory's controls."""

import copy
import json
from dataclasses import dataclass, field
from typing import Mapping

FIDELITY_LEVELS = frozenset({"analytical", "reduced-order", "surrogate", "empirical", "hybrid"})
ACTION_KINDS = frozenset({"configure", "control", "intervention", "measurement", "wait"})


def _strings(name, values, *, allow_empty=False):
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} requires a sequence of strings")
    result = tuple(values)
    if (not result and not allow_empty) or any(
        not isinstance(value, str) or not value.strip() for value in result
    ):
        raise ValueError(f"{name} requires nonempty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} cannot contain duplicates")
    return result


def _variables(name, values, *, allow_empty=False):
    if not isinstance(values, Mapping) or (not values and not allow_empty):
        raise ValueError(f"{name} requires at least one named variable")
    result = {}
    for variable, specification in values.items():
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError(f"{name} variable names must be nonempty strings")
        if not isinstance(specification, Mapping):
            raise ValueError(f"{name}.{variable} must be an object")
        description = specification.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{name}.{variable} requires a description")
        unit = specification.get("unit")
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            raise ValueError(f"{name}.{variable}.unit must be a string or null")
        result[variable] = copy.deepcopy(dict(specification))
        result[variable]["unit"] = unit
    return result


@dataclass(frozen=True)
class ResearchContract:
    """Machine-readable scientific scope without exposing a specimen's hidden state."""

    domains: tuple[str, ...]
    phenomena: tuple[str, ...]
    questions: tuple[str, ...]
    observables: Mapping[str, Mapping[str, object]]
    latent_variables: Mapping[str, Mapping[str, object]]
    interventions: tuple[str, ...]
    invariants: tuple[str, ...]
    validity_conditions: tuple[str, ...]
    limitations: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    fidelity: str
    action_semantics: Mapping[str, Mapping[str, object]]
    reference_methods: tuple[str, ...] = ()
    physical_counterpart: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def describe(self, action_names):
        action_names = set(action_names)
        domains = _strings("domains", self.domains)
        phenomena = _strings("phenomena", self.phenomena)
        questions = _strings("questions", self.questions)
        interventions = _strings("interventions", self.interventions, allow_empty=True)
        invariants = _strings("invariants", self.invariants, allow_empty=True)
        validity = _strings("validity_conditions", self.validity_conditions)
        limitations = _strings("limitations", self.limitations)
        failures = _strings("failure_conditions", self.failure_conditions, allow_empty=True)
        references = _strings("reference_methods", self.reference_methods, allow_empty=True)
        if self.fidelity not in FIDELITY_LEVELS:
            raise ValueError(f"fidelity must be one of {sorted(FIDELITY_LEVELS)}")
        if not set(interventions) <= action_names:
            unknown = sorted(set(interventions) - action_names)
            raise ValueError(f"Research interventions reference unknown actions: {unknown}")
        if set(self.action_semantics) != action_names:
            missing = sorted(action_names - set(self.action_semantics))
            extra = sorted(set(self.action_semantics) - action_names)
            raise ValueError(
                f"Action semantics must cover every action; missing={missing}, extra={extra}"
            )
        semantics = {}
        for action, specification in self.action_semantics.items():
            if not isinstance(specification, Mapping):
                raise ValueError(f"action_semantics.{action} must be an object")
            kind = specification.get("kind")
            description = specification.get("description")
            if kind not in ACTION_KINDS:
                raise ValueError(
                    f"action_semantics.{action}.kind must be one of {sorted(ACTION_KINDS)}"
                )
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"action_semantics.{action} requires a description")
            semantics[action] = copy.deepcopy(dict(specification))
        if self.physical_counterpart is not None and (
            not isinstance(self.physical_counterpart, str) or not self.physical_counterpart.strip()
        ):
            raise ValueError("physical_counterpart must be a nonempty string or null")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be an object")
        result = {
            "schema_version": 1,
            "domains": list(domains),
            "phenomena": list(phenomena),
            "questions": list(questions),
            "observables": _variables("observables", self.observables),
            "latent_variables": _variables(
                "latent_variables", self.latent_variables, allow_empty=True
            ),
            "interventions": list(interventions),
            "invariants": list(invariants),
            "failure_conditions": list(failures),
            "validity": {
                "fidelity": self.fidelity,
                "conditions": list(validity),
                "limitations": list(limitations),
            },
            "action_semantics": semantics,
            "reference_methods": list(references),
            "physical_counterpart": self.physical_counterpart,
            "metadata": copy.deepcopy(dict(self.metadata)),
        }
        try:
            json.dumps(result, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Research contract must contain finite JSON values") from exc
        return result
