"""Builtin memory_admin plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.memory_admin.tools import memory_admin_function_bindings


class BuiltinMemoryAdminPlugin(BasePlugin):
    plugin_id = "memory_admin"
    plugin_name = "memory_admin"
    plugin_description = "Memory administration tools."

    def functions(self) -> list[FunctionBinding]:
        return memory_admin_function_bindings()


plugin = BuiltinMemoryAdminPlugin
