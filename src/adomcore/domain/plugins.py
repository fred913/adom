"""Plugin manifest (BaseModel for YAML parsing) and descriptor for runtime."""

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
