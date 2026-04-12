"""Builtin SSH plugin tools."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("ssh")


class SSHSessionPool:
    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}

    def function_bindings(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="ssh_open_session",
                    description="Open an SSH session and return a session id.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string"},
                            "username": {"type": "string"},
                            "port": {"type": "integer", "default": 22},
                            "password": {"type": ["string", "null"]},
                            "key_filename": {"type": ["string", "null"]},
                            "timeout": {"type": "number", "default": 10},
                        },
                        "required": ["host", "username"],
                    },
                    source_plugin=_PLUGIN_ID,
                ),
                handler=self.open_session,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="ssh_execute_command",
                    description="Execute a command using an open SSH session.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "command": {"type": "string"},
                            "timeout": {"type": "number", "default": 30},
                        },
                        "required": ["session_id", "command"],
                    },
                    source_plugin=_PLUGIN_ID,
                ),
                handler=self.execute_command,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="ssh_close_session",
                    description="Terminate an open SSH session.",
                    input_schema={
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                    },
                    source_plugin=_PLUGIN_ID,
                ),
                handler=self.close_session,
            ),
        ]

    def open_session(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: str | None = None,
        key_filename: str | None = None,
        timeout: float = 10,
    ) -> dict[str, Any]:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            key_filename=key_filename,
            timeout=timeout,
        )
        session_id = uuid4().hex
        self._clients[session_id] = client
        return {
            "session_id": session_id,
            "host": host,
            "port": port,
            "username": username,
        }

    def execute_command(
        self, session_id: str, command: str, timeout: float = 30
    ) -> dict[str, Any]:
        client = self._clients.get(session_id)
        if client is None:
            raise KeyError(f"SSH session not found: {session_id}")
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        del stdin
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        return {
            "session_id": session_id,
            "command": command,
            "exit_status": exit_status,
            "stdout": output,
            "stderr": error,
        }

    def close_session(self, session_id: str) -> dict[str, str]:
        client = self._clients.pop(session_id, None)
        if client is None:
            raise KeyError(f"SSH session not found: {session_id}")
        client.close()
        return {"session_id": session_id, "status": "closed"}


def ssh_function_bindings() -> list[FunctionBinding]:
    return SSHSessionPool().function_bindings()
