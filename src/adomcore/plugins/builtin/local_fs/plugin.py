"""Builtin local_fs plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.local_fs.tools import local_fs_function_bindings


class BuiltinLocalFsPlugin(BasePlugin):
    plugin_id = "local_fs"
    plugin_name = "local_fs"
    plugin_description = (
        "Local filesystem tools for reading, writing, and listing files."
    )

    def functions(self) -> list[FunctionBinding]:
        return local_fs_function_bindings()


plugin = BuiltinLocalFsPlugin
