"""Builtin cron plugin — expose cron tools to the agent."""

from adomcore.plugins.builtin.cron.tools import register_cron_tools
from adomcore.plugins.context import PluginContext


class BuiltinCronPlugin:
    def setup(self, ctx: PluginContext) -> None:
        register_cron_tools(ctx)


plugin = BuiltinCronPlugin
