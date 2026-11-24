"""Reference models and independently installed model providers."""

from functools import lru_cache
from importlib.metadata import entry_points

from .battery import Battery
from .optics import FiberBench
from .thermal import ThermalBench

BUILTINS = {model.name: model for model in (FiberBench, ThermalBench, Battery)}


@lru_cache(maxsize=1)
def registry():
    providers = dict(BUILTINS)
    for entry in entry_points(group="synthetic_lab.models"):
        if entry.name in providers:
            raise ValueError(f"Duplicate model name {entry.name!r}")
        providers[entry.name] = entry
    return providers


def available():
    return sorted(registry())


def load(name, config=None):
    provider = registry().get(name)
    if provider is None:
        raise ValueError(f"Unknown laboratory {name!r}; choose from {available()}")
    factory = provider if isinstance(provider, type) else provider.load()
    return factory(config)
