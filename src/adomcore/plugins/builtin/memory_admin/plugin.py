"""Builtin memory_admin plugin."""

from adomcore.plugins.builtin.memory_admin.tools import register_memory_admin_tools
from adomcore.plugins.context import PluginContext


class BuiltinMemoryAdminPlugin:
    def setup(self, ctx: PluginContext) -> None:
        register_memory_admin_tools(ctx)


plugin = BuiltinMemoryAdminPlugin
