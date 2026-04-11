"""Plugin protocol and defaults for declarative plugin capabilities."""

from typing import Protocol, runtime_checkable

from adomcore.domain.capabilities import FunctionBinding
from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import (
    PluginDescriptor,
    bind_plugin_metadata,
    descriptor_from_plugin,
)
from adomcore.domain.skills import SkillSpec


@runtime_checkable
class Plugin(Protocol):
    id: PluginId
    name: str
    version: str
    description: str
    entry_point: str
    builtin: bool
    enabled: bool
    manifest_path: str | None

    def functions(self) -> list[FunctionBinding]: ...

    def skills(self) -> list[SkillSpec]: ...

    def system_prompt(self) -> str: ...


class BasePlugin:
    plugin_id: PluginId | str = ""
    plugin_name: str = ""
    plugin_version: str = "0.1.0"
    plugin_description: str = ""
    plugin_entry_point: str = ""
    plugin_builtin: bool = False
    plugin_enabled: bool = True
    plugin_manifest_path: str | None = None

    def __init__(
        self,
        *,
        plugin_id: PluginId | str | None = None,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        entry_point: str | None = None,
        builtin: bool | None = None,
        enabled: bool | None = None,
        manifest_path: str | None = None,
    ) -> None:
        cls = type(self)
        self.id = PluginId(str(plugin_id if plugin_id is not None else cls.plugin_id))
        self.name = name if name is not None else cls.plugin_name
        self.version = version if version is not None else cls.plugin_version
        self.description = (
            description if description is not None else cls.plugin_description
        )
        self.entry_point = (
            entry_point if entry_point is not None else cls.plugin_entry_point
        )
        self.builtin = builtin if builtin is not None else cls.plugin_builtin
        self.enabled = enabled if enabled is not None else cls.plugin_enabled
        self.manifest_path = (
            manifest_path if manifest_path is not None else cls.plugin_manifest_path
        )

    def bind_descriptor(self, descriptor: PluginDescriptor) -> BasePlugin:
        bind_plugin_metadata(self, descriptor)
        return self

    def descriptor(self) -> PluginDescriptor:
        return descriptor_from_plugin(self)

    @classmethod
    def metadata_only(cls, descriptor: PluginDescriptor) -> BasePlugin:
        return cls().bind_descriptor(descriptor)

    def functions(self) -> list[FunctionBinding]:
        return []

    def skills(self) -> list[SkillSpec]:
        return []

    def system_prompt(self) -> str:
        return ""
