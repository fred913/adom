"""Capability registry — in-memory store of registered FunctionSpecs."""

from collections.abc import Callable
from typing import Any

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import PluginId


class CapabilityRegistry:
    """In-memory registry of callable functions exposed to the agent.

    Handlers are stored separately from specs so specs can be serialised
    without pickling callables.
    """

    def __init__(self) -> None:
        self._specs: dict[str, FunctionSpec] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        spec: FunctionSpec,
        handler: Callable[..., Any],
    ) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def unregister(self, name: str) -> None:
        self._specs.pop(name, None)
        self._handlers.pop(name, None)

    def unregister_by_plugin(self, plugin_id: PluginId) -> None:
        to_remove = [
            name
            for name, spec in self._specs.items()
            if spec.source_plugin == plugin_id
        ]
        for name in to_remove:
            self.unregister(name)

    def get_spec(self, name: str) -> FunctionSpec | None:
        return self._specs.get(name)

    def get_handler(self, name: str) -> Callable[..., Any] | None:
        return self._handlers.get(name)

    def list_enabled(self) -> list[FunctionSpec]:
        return [s for s in self._specs.values() if s.enabled]

    def list_all(self) -> list[FunctionSpec]:
        return list(self._specs.values())
