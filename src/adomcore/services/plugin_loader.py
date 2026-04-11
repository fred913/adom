"""Plugin loader — discover and import plugin Python modules."""

import importlib
import sys
from pathlib import Path
from typing import cast

from loguru import logger

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor, bind_plugin_metadata
from adomcore.plugins.base import Plugin


class PluginLoader:
    def load(self, descriptor: PluginDescriptor) -> Plugin:
        """Import and return the plugin instance from its entry_point."""
        module_path, attr = descriptor.entry_point.rsplit(":", 1)
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            # Try loading from manifest_path directory
            if descriptor.manifest_path:
                plugin_dir = Path(descriptor.manifest_path).parent
                self._add_to_path(plugin_dir)
                module = importlib.import_module(module_path)
            else:
                raise
        raw_plugin = getattr(module, attr)
        plugin = self._coerce_plugin(raw_plugin)
        bind_plugin_metadata(plugin, descriptor)
        return plugin

    def load_builtin(self, descriptor_or_id: PluginDescriptor | PluginId) -> Plugin:
        descriptor = self._builtin_descriptor(descriptor_or_id)
        module_path = f"adomcore.plugins.builtin.{descriptor.id}.plugin"
        module = importlib.import_module(module_path)
        raw_plugin = getattr(module, "plugin")
        plugin = self._coerce_plugin(raw_plugin)
        bind_plugin_metadata(plugin, descriptor)
        return plugin

    @staticmethod
    def _builtin_descriptor(
        descriptor_or_id: PluginDescriptor | PluginId,
    ) -> PluginDescriptor:
        if isinstance(descriptor_or_id, PluginDescriptor):
            return descriptor_or_id
        plugin_id = descriptor_or_id
        return PluginDescriptor(
            id=plugin_id,
            name=str(plugin_id),
            version="builtin",
            description="",
            entry_point=f"adomcore.plugins.builtin.{plugin_id}.plugin:plugin",
            builtin=True,
            enabled=True,
        )

    @staticmethod
    def _coerce_plugin(raw_plugin: object) -> Plugin:
        if callable(raw_plugin) and not isinstance(raw_plugin, type):
            return cast(Plugin, raw_plugin())
        if isinstance(raw_plugin, type):
            return cast(Plugin, raw_plugin())
        return cast(Plugin, raw_plugin)

    @staticmethod
    def _add_to_path(directory: Path) -> None:
        path_str = str(directory)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            logger.debug("Added {} to sys.path", path_str)
