"""Plugin manager — install, enable, disable plugins."""

from loguru import logger

from adomcore.domain.capabilities import FunctionBinding
from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor, descriptor_from_plugin
from adomcore.domain.skills import SkillSpec
from adomcore.plugins.base import BasePlugin, Plugin
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.plugin_loader import PluginLoader
from adomcore.storage.stores.plugin_store import PluginStore


class PluginManager:
    def __init__(
        self,
        store: PluginStore,
        loader: PluginLoader,
        registry: CapabilityRegistry,
    ) -> None:
        self._store = store
        self._loader = loader
        self._registry = registry
        self._plugins: dict[PluginId, Plugin] = {}
        self._persisted_plugin_ids: set[PluginId] = set()
        self._registry.register_provider("plugins", self.function_bindings)

    async def load_all(self) -> None:
        for pid in list(self._persisted_plugin_ids):
            self._plugins.pop(pid, None)
        self._persisted_plugin_ids.clear()

        for desc in self._store.load_registry():
            self._persisted_plugin_ids.add(desc.id)
            if desc.enabled:
                await self._activate(desc)
            else:
                self._plugins[desc.id] = BasePlugin.metadata_only(desc)

    async def _activate(self, desc: PluginDescriptor) -> None:
        try:
            if desc.builtin:
                instance = self._loader.load_builtin(desc)
            else:
                instance = self._loader.load(desc)
            self.activate_instance(instance)
            logger.info("Plugin activated: {}", instance.id)
        except Exception:
            logger.exception("Failed to activate plugin: {}", desc.id)

    def activate_instance(self, instance: Plugin) -> None:
        pid = instance.id
        if not pid:
            raise ValueError("Plugin instance is missing bound metadata: id")
        instance.enabled = True
        self._plugins[pid] = instance

    async def enable(self, pid: PluginId) -> None:
        plugin = self._plugins.get(pid)
        if plugin is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        updated = descriptor_from_plugin(plugin).model_copy(update={"enabled": True})
        await self._activate(updated)
        await self._save_registry()

    async def disable(self, pid: PluginId) -> None:
        plugin = self._plugins.get(pid)
        if plugin is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        updated = descriptor_from_plugin(plugin).model_copy(update={"enabled": False})
        self._plugins[pid] = BasePlugin.metadata_only(updated)
        await self._save_registry()

    async def _save_registry(self) -> None:
        await self._store.save_registry(
            [
                descriptor_from_plugin(self._plugins[pid])
                for pid in self._persisted_plugin_ids
                if pid in self._plugins
            ]
        )

    def list_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def function_bindings(self) -> list[FunctionBinding]:
        bindings: list[FunctionBinding] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            try:
                bindings.extend(plugin.functions())
            except Exception:
                logger.exception(
                    "Failed to compute plugin functions dynamically: {}", plugin.id
                )
        return bindings

    def list_enabled_skills(self) -> list[SkillSpec]:
        skills: list[SkillSpec] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            try:
                skills.extend(plugin.skills())
            except Exception:
                logger.exception(
                    "Failed to compute plugin skills dynamically: {}", plugin.id
                )
        return skills

    async def activate_builtin(self, pid: PluginId) -> None:
        desc = PluginDescriptor(
            id=pid,
            name=str(pid),
            version="builtin",
            description="",
            entry_point=f"adomcore.plugins.builtin.{pid}.plugin:plugin",
            builtin=True,
            enabled=True,
        )
        await self._activate(desc)

    def system_prompt_parts(self) -> list[str]:
        parts: list[str] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            try:
                prompt = plugin.system_prompt().strip()
            except Exception:
                logger.exception(
                    "Failed to compute plugin system prompt dynamically: {}",
                    plugin.id,
                )
                continue
            if prompt:
                parts.append(prompt)
        return parts
