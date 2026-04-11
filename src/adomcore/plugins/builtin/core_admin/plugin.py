"""Builtin core_admin plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.core_admin.tools import core_admin_function_bindings


class BuiltinCoreAdminPlugin(BasePlugin):
    plugin_id = "core_admin"
    plugin_name = "core_admin"
    plugin_version = "builtin"
    plugin_builtin = True

    def functions(self) -> list[FunctionBinding]:
        return core_admin_function_bindings()


plugin = BuiltinCoreAdminPlugin
