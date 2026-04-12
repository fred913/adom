"""Plugin manager — install, enable, disable plugins."""

from loguru import logger

from adomcore.domain.capabilities import FunctionBinding
from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor, descriptor_from_plugin
from adomcore.domain.skills import SkillSpec
from adomcore.plugins.base import BasePlugin, Plugin, SystemPromptValue
from adomcore.plugins.builtin import builtin_plugin_descriptors
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.plugin_loader import PluginLoader
from adomcore.storage.stores.plugin_store import PluginStore


class PluginManager:
    def __init__(
        self,
        store: PluginStore,
        loader: PluginLoader,
        registry: CapabilityRegistry,
        builtin_descriptors: list[PluginDescriptor] | None = None,
    ) -> None:
        self._store = store
        self._loader = loader
        self._registry = registry
        self._plugins: dict[PluginId, Plugin] = {}
        self._persisted_plugin_ids: set[PluginId] = set()
        self._builtin_descriptors = builtin_descriptors or builtin_plugin_descriptors()
        self._registry.register_provider("plugins", self.function_bindings)

    async def load_all(self) -> None:
        self._plugins.clear()
        self._persisted_plugin_ids.clear()

        for desc in self._builtin_descriptors:
            if desc.enabled:
                await self._activate(desc)
            else:
                self._plugins[desc.id] = BasePlugin.metadata_only(desc)

        for desc in self._store.load_registry():
            self._persisted_plugin_ids.add(desc.id)
            if desc.enabled:
                await self._activate(desc)
            else:
                self._plugins[desc.id] = BasePlugin.metadata_only(desc)

    async def _activate(self, desc: PluginDescriptor) -> None:
        try:
            instance = self._loader.load(desc)
            self.activate_instance(instance)
        except Exception:
            logger.exception("Failed to activate plugin: {}", desc.id)

    def activate_instance(self, instance: Plugin) -> None:
        pid = instance.id
        if not pid:
            raise ValueError("Plugin instance is missing bound metadata: id")
        instance.enabled = True
        self._plugins[pid] = instance
        logger.info("Plugin activated: {}", instance.id)

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

    def system_prompt_parts(self) -> list[str]:
        prioritized_parts: list[tuple[int | float, str]] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            try:
                prompt_value = plugin.system_prompt()
            except Exception:
                logger.exception(
                    "Failed to compute plugin system prompt dynamically: {}",
                    plugin.id,
                )
                continue
            prompt, priority = self._normalize_system_prompt(prompt_value)
            if prompt:
                prioritized_parts.append((priority, prompt))
        prioritized_parts.sort(key=lambda item: item[0], reverse=True)
        return [prompt for _, prompt in prioritized_parts]

    @staticmethod
    def _normalize_system_prompt(
        prompt_value: SystemPromptValue,
    ) -> tuple[str, int | float]:
        if isinstance(prompt_value, tuple):
            prompt, priority = prompt_value
            return prompt.strip(), priority
        return prompt_value.strip(), 0
