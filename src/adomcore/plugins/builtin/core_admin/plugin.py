"""Builtin core_admin plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.core_admin.tools import core_admin_function_bindings


class BuiltinCoreAdminPlugin(BasePlugin):
    plugin_id = "core_admin"
    plugin_name = "core_admin"
    plugin_description = (
        "Core administration tools that is deeply integrated with the agent itself."
    )

    def functions(self) -> list[FunctionBinding]:
        return core_admin_function_bindings()


plugin = BuiltinCoreAdminPlugin
