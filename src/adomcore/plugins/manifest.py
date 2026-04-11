"""PluginManifest — parsed from manifest.yaml."""

from pydantic import BaseModel


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    entry_point: str = "plugin:plugin"
    builtin: bool = False
