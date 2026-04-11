"""Plugin schemas."""

from pydantic import BaseModel


class PluginResponse(BaseModel):
    id: str
    name: str
    version: str
    enabled: bool
    builtin: bool
