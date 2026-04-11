"""Builtin core_admin plugin."""

from adomcore.plugins.builtin.core_admin.tools import register_core_admin_tools
from adomcore.plugins.context import PluginContext


class BuiltinCoreAdminPlugin:
    def setup(self, ctx: PluginContext) -> None:
        register_core_admin_tools(ctx)


plugin = BuiltinCoreAdminPlugin
