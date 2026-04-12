"""Builtin SSH plugin."""

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.ssh.tools import SSHSessionPool


class BuiltinSshPlugin(BasePlugin):
    plugin_id = "ssh"
    plugin_name = "ssh"
    plugin_description = "SSH session management and remote command execution tools."

    def __init__(self) -> None:
        super().__init__()
        self._pool = SSHSessionPool()

    def functions(self) -> list[FunctionBinding]:
        return self._pool.function_bindings()


plugin = BuiltinSshPlugin
