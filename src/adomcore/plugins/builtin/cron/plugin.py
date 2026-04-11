"""Builtin cron plugin — expose cron tools to the agent."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.cron.tools import cron_function_bindings


class BuiltinCronPlugin(BasePlugin):
    plugin_id = "cron"
    plugin_name = "cron"
    plugin_version = "builtin"
    plugin_builtin = True

    def functions(self) -> list[FunctionBinding]:
        return cron_function_bindings()


plugin = BuiltinCronPlugin
