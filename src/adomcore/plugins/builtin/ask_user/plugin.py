"""Builtin AskUser plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.ask_user.tools import ask_user_function_bindings


class BuiltinAskUserPlugin(BasePlugin):
    plugin_id = "ask_user"
    plugin_name = "ask_user"
    plugin_description = "Interactive local-console user prompting via questionary."

    def functions(self) -> list[FunctionBinding]:
        return ask_user_function_bindings()


plugin = BuiltinAskUserPlugin
