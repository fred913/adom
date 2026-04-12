"""Plugin loader — discover and import plugin Python modules."""

import inspect
import importlib
import sys
from pathlib import Path
from typing import Any
from typing import cast

from loguru import logger

from adomcore.domain.plugins import PluginDescriptor, bind_plugin_metadata
from adomcore.plugins.base import Plugin


class PluginLoader:
    def __init__(self, plugin_config: dict[str, dict[str, Any]] | None = None) -> None:
        self._plugin_config = plugin_config or {}

    def load(self, descriptor: PluginDescriptor) -> Plugin:
        """Import and return the plugin instance from the plugin module."""
        module_path = "plugin"
        attr = "plugin"
        if descriptor.manifest_path:
            plugin_dir = Path(descriptor.manifest_path).parent
            self._add_to_path(plugin_dir)
            importlib.invalidate_caches()
            sys.modules.pop(module_path, None)
        else:
            module_path = f"adomcore.plugins.builtin.{descriptor.id}.plugin"
        module = importlib.import_module(module_path)
        raw_plugin = getattr(module, attr)
        plugin = self._coerce_plugin(raw_plugin, self._plugin_config.get(str(descriptor.id), {}))
        bind_plugin_metadata(plugin, descriptor)
        return plugin

    @staticmethod
    def _coerce_plugin(raw_plugin: object, config: dict[str, Any]) -> Plugin:
        if callable(raw_plugin) and not isinstance(raw_plugin, type):
            return cast(Plugin, PluginLoader._instantiate(raw_plugin, config))
        if isinstance(raw_plugin, type):
            return cast(Plugin, PluginLoader._instantiate(raw_plugin, config))
        return cast(Plugin, raw_plugin)

    @staticmethod
    def _instantiate(factory: object, config: dict[str, Any]) -> object:
        signature = inspect.signature(cast(Any, factory))
        if "config" in signature.parameters:
            return cast(Any, factory)(config=config)
        return cast(Any, factory)()

    @staticmethod
    def _add_to_path(directory: Path) -> None:
        path_str = str(directory)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            logger.debug("Added {} to sys.path", path_str)
