"""Plugin manager — install, enable, disable plugins."""

import inspect

from loguru import logger

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor
from adomcore.plugins.base import Plugin
from adomcore.plugins.context import PluginContext
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.plugin_loader import PluginLoader
from adomcore.storage.stores.plugin_store import PluginStore


class PluginManager:
    def __init__(
        self,
        store: PluginStore,
        loader: PluginLoader,
        registry: CapabilityRegistry,
        context_factory: PluginContext,
    ) -> None:
        self._store = store
        self._loader = loader
        self._registry = registry
        self._ctx = context_factory
        self._descriptors: dict[PluginId, PluginDescriptor] = {}
        self._instances: dict[PluginId, Plugin] = {}

    async def load_all(self) -> None:
        for desc in self._store.load_registry():
            self._descriptors[desc.id] = desc
            if desc.enabled:
                await self._activate(desc)

    async def _activate(self, desc: PluginDescriptor) -> None:
        try:
            if desc.builtin:
                instance = self._loader.load_builtin(desc.id)
            else:
                instance = self._loader.load(desc)
            await self._run_setup(instance)
            self._instances[desc.id] = instance
            logger.info("Plugin activated: {}", desc.id)
        except Exception:
            logger.exception("Failed to activate plugin: {}", desc.id)

    async def _run_setup(self, instance: Plugin) -> None:
        result = instance.setup(self._ctx)
        if inspect.isawaitable(result):
            await result

    async def enable(self, pid: PluginId) -> None:
        desc = self._descriptors.get(pid)
        if desc is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        updated = desc.model_copy(update={"enabled": True})
        self._descriptors[pid] = updated
        await self._activate(updated)
        await self._store.save_registry(list(self._descriptors.values()))

    async def disable(self, pid: PluginId) -> None:
        desc = self._descriptors.get(pid)
        if desc is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        self._descriptors[pid] = desc.model_copy(update={"enabled": False})
        self._instances.pop(pid, None)
        self._registry.unregister_by_plugin(pid)
        await self._store.save_registry(list(self._descriptors.values()))

    def list_all(self) -> list[PluginDescriptor]:
        return list(self._descriptors.values())
