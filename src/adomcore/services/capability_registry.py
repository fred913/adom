"""Capability registry — in-memory store of registered FunctionSpecs."""

from collections.abc import Callable
from typing import Any

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId


class CapabilityRegistry:
    """In-memory registry of callable functions exposed to the agent.

    Handlers are stored separately from specs so specs can be serialised
    without pickling callables.
    """

    def __init__(self) -> None:
        self._specs: dict[str, FunctionSpec] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._providers: dict[str, Callable[[], list[FunctionBinding]]] = {}

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

    def register_provider(
        self,
        provider_name: str,
        provider: Callable[[], list[FunctionBinding]],
    ) -> None:
        self._providers[provider_name] = provider

    def unregister_provider(self, provider_name: str) -> None:
        self._providers.pop(provider_name, None)

    def unregister_by_plugin(self, plugin_id: PluginId) -> None:
        to_remove = [
            name
            for name, spec in self._specs.items()
            if spec.source_plugin == plugin_id
        ]
        for name in to_remove:
            self.unregister(name)

    def get_spec(self, name: str) -> FunctionSpec | None:
        specs, _ = self._snapshot()
        return specs.get(name)

    def get_handler(self, name: str) -> Callable[..., Any] | None:
        _, handlers = self._snapshot()
        return handlers.get(name)

    def list_enabled(self) -> list[FunctionSpec]:
        specs, _ = self._snapshot()
        return [s for s in specs.values() if s.enabled]

    def list_all(self) -> list[FunctionSpec]:
        specs, _ = self._snapshot()
        return list(specs.values())

    def _snapshot(
        self,
    ) -> tuple[dict[str, FunctionSpec], dict[str, Callable[..., Any]]]:
        specs = dict(self._specs)
        handlers = dict(self._handlers)
        for provider in self._providers.values():
            for binding in provider():
                specs[binding.spec.name] = binding.spec
                handlers[binding.spec.name] = binding.handler
        return specs, handlers
