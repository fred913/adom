"""Plugin manifest and runtime metadata helpers."""

from typing import Protocol

from pydantic import BaseModel

from adomcore.domain.ids import PluginId


class PluginManifestModel(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    entry_point: str = "plugin:plugin"
    builtin: bool = False


class PluginDescriptor(BaseModel):
    id: PluginId
    name: str
    version: str
    description: str
    entry_point: str
    builtin: bool
    enabled: bool = True
    manifest_path: str | None = None


class PluginMetadata(Protocol):
    id: PluginId
    name: str
    version: str
    description: str
    entry_point: str
    builtin: bool
    enabled: bool
    manifest_path: str | None


def bind_plugin_metadata(plugin: object, descriptor: PluginDescriptor) -> None:
    """Attach persisted plugin metadata directly onto a plugin instance."""
    setattr(plugin, "id", descriptor.id)
    setattr(plugin, "name", descriptor.name)
    setattr(plugin, "version", descriptor.version)
    setattr(plugin, "description", descriptor.description)
    setattr(plugin, "entry_point", descriptor.entry_point)
    setattr(plugin, "builtin", descriptor.builtin)
    setattr(plugin, "enabled", descriptor.enabled)
    setattr(plugin, "manifest_path", descriptor.manifest_path)


def descriptor_from_plugin(plugin: PluginMetadata) -> PluginDescriptor:
    """Reconstruct a persisted descriptor from a metadata-bound plugin instance."""
    return PluginDescriptor(
        id=plugin.id,
        name=plugin.name,
        version=plugin.version,
        description=plugin.description,
        entry_point=plugin.entry_point,
        builtin=plugin.builtin,
        enabled=plugin.enabled,
        manifest_path=plugin.manifest_path,
    )
