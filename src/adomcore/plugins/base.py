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
from adomcore.plugins.context import PluginContext

type SystemPromptValue = str | tuple[str, int | float]


@runtime_checkable
class Plugin(Protocol):
    id: PluginId
    name: str
    version: str
    description: str
    manifest_path: str | None

    def functions(self) -> list[FunctionBinding]: ...

    def skills(self) -> list[SkillSpec]: ...

    def system_prompt(self) -> SystemPromptValue: ...

    def bind_context(self, context: PluginContext) -> Plugin: ...


class BasePlugin:
    plugin_id: PluginId | str = ""
    plugin_name: str = ""
    plugin_version: str = "0.1.0"
    plugin_description: str = ""
    plugin_manifest_path: str | None = None

    def __init__(
        self,
    ) -> None:
        cls = type(self)
        self.id = PluginId(cls.plugin_id)
        self.name = cls.plugin_name
        self.version = cls.plugin_version
        self.description = cls.plugin_description
        self.manifest_path = cls.plugin_manifest_path

    def bind_descriptor(self, descriptor: PluginDescriptor) -> BasePlugin:
        bind_plugin_metadata(self, descriptor)
        return self

    def bind_context(self, context: PluginContext) -> BasePlugin:
        self._context = context
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

    def system_prompt(self) -> SystemPromptValue:
        return ""
