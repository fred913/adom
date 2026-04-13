"""Plugin manager — install, enable, disable plugins."""

from loguru import logger

from adomcore.domain.capabilities import FunctionBinding
from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor, descriptor_from_plugin
from adomcore.domain.skills import SkillSpec
from adomcore.plugins.base import BasePlugin, Plugin, SystemPromptValue
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
        plugin_context: PluginContext | None = None,
    ) -> None:
        self._store = store
        self._loader = loader
        self._registry = registry
        self._plugin_context = plugin_context
        self._plugins: dict[PluginId, Plugin] = {}
        self._descriptors: dict[PluginId, PluginDescriptor] = {}
        self._persisted_plugin_ids: set[PluginId] = set()
        for desc in self._store.load_registry():
            self._persisted_plugin_ids.add(desc.id)
            self._descriptors[desc.id] = desc
            self._plugins[desc.id] = BasePlugin.metadata_only(desc)
        self._registry.register_provider("plugins", self.function_bindings)

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
        if self._plugin_context is not None:
            instance = instance.bind_context(self._plugin_context)
        self._descriptors[pid] = descriptor_from_plugin(instance).model_copy(
            update={"enabled": True}
        )
        self._plugins[pid] = instance
        logger.info("Plugin activated: {}", instance.id)

    async def enable(self, pid: PluginId) -> None:
        descriptor = self._descriptors.get(pid)
        if descriptor is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        updated = descriptor.model_copy(update={"enabled": True})
        self._descriptors[pid] = updated
        await self._activate(updated)
        await self._save_registry()

    async def disable(self, pid: PluginId) -> None:
        descriptor = self._descriptors.get(pid)
        if descriptor is None:
            raise KeyError(f"Plugin not found: {pid!r}")
        updated = descriptor.model_copy(update={"enabled": False})
        self._descriptors[pid] = updated
        self._plugins[pid] = BasePlugin.metadata_only(updated)
        await self._save_registry()

    async def _save_registry(self) -> None:
        await self._store.save_registry(
            [
                self._descriptors[pid]
                for pid in self._persisted_plugin_ids
                if pid in self._plugins
            ]
        )

    def list_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def is_enabled(self, pid: PluginId) -> bool:
        descriptor = self._descriptors.get(pid)
        return descriptor.enabled if descriptor is not None else False

    def function_bindings(self) -> list[FunctionBinding]:
        bindings: list[FunctionBinding] = []
        for plugin in self._plugins.values():
            if not self.is_enabled(plugin.id):
                continue
            if type(plugin) is BasePlugin:
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
            if not self.is_enabled(plugin.id):
                continue
            if type(plugin) is BasePlugin:
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
            if not self.is_enabled(plugin.id):
                continue
            if type(plugin) is BasePlugin:
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
