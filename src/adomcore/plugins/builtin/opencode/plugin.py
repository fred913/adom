"""Builtin opencode plugin."""

from typing import Any

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.opencode.tools import OpencodeToolset
from adomcore.plugins.context import PluginContext


class BuiltinOpencodePlugin(BasePlugin):
    plugin_id = "opencode"
    plugin_name = "opencode"
    plugin_description = "Delegate tasks to an opencode HTTP server and reuse an active opencode session."

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._tools = OpencodeToolset(config)

    def bind_context(self, context: PluginContext) -> BuiltinOpencodePlugin:
        super().bind_context(context)
        self._tools.bind_context(context)
        return self

    def functions(self) -> list[FunctionBinding]:
        return self._tools.function_bindings()

    def system_prompt(self) -> str:
        return (
            "Use the opencode_execute_task tool when you need to delegate a coding or repository "
            "task to an opencode server. The tool automatically starts opencode serve on first "
            "use if needed and reuses the same reachable opencode session on later calls. "
            "NOTE: If this tool fails, and the user's instruction is to write code, warn the user what "
            "happened and ask for clarification before proceeding with another tool that is not specialized for coding tasks."
        )


plugin = BuiltinOpencodePlugin
