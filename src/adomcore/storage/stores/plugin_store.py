"""Plugin store — registry.json5 + per-plugin state.json5."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class PluginStore:
    _adapter = TypeAdapter(list[PluginDescriptor])

    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    def load_registry(self) -> list[PluginDescriptor]:
        data: list[dict[str, Any]] | None = self._json5.read(
            self._paths.plugin_registry
        )
        if data is None:
            return []
        return self._adapter.validate_python(data)

    async def save_registry(self, descriptors: list[PluginDescriptor]) -> None:
        data = [descriptor.model_dump(mode="json") for descriptor in descriptors]
        await self._json5.write(self._paths.plugin_registry, data)

    def load_plugin_state(self, pid: PluginId) -> dict[str, Any] | None:
        return self._json5.read(self._paths.plugin_state(pid))

    async def save_plugin_state(self, pid: PluginId, state: dict[str, Any]) -> None:
        await self._json5.write(self._paths.plugin_state(pid), state)
