"""Plugin loader — discover and import plugin Python modules."""

import importlib
import sys
from pathlib import Path
from typing import cast

from loguru import logger

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor
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
        plugin: Plugin = getattr(module, attr)
        if callable(plugin) and not isinstance(plugin, type):
            return plugin
        if isinstance(plugin, type):
            return cast(Plugin, plugin())
        return plugin

    def load_builtin(self, plugin_id: PluginId) -> Plugin:
        module_path = f"adomcore.plugins.builtin.{plugin_id}.plugin"
        module = importlib.import_module(module_path)
        cls = getattr(module, "plugin")
        return cast(Plugin, cls() if isinstance(cls, type) else cls)

    @staticmethod
    def _add_to_path(directory: Path) -> None:
        path_str = str(directory)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            logger.debug("Added {} to sys.path", path_str)
