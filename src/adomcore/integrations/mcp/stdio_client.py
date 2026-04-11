"""Stdio MCP client — launch subprocess, manage stdin/stdout JSON-RPC."""

import asyncio
import json
from typing import Any

from loguru import logger

from adomcore.domain.mcp import McpServerSpec, McpToolSpec


class StdioMcpClient:
    def __init__(self, spec: McpServerSpec) -> None:
        self._spec = spec
        self._proc: asyncio.subprocess.Process | None = None
        self._seq = 0

    async def start(self) -> None:
        import os

        env = {**os.environ, **self._spec.env}
        self._proc = await asyncio.create_subprocess_exec(
            self._spec.command,
            *self._spec.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        logger.debug("MCP process started: {}", self._spec.id)

    async def stop(self) -> None:
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            await self._proc.wait()

    async def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        assert self._proc and self._proc.stdin and self._proc.stdout
        self._seq += 1
        req = json.dumps(
            {"jsonrpc": "2.0", "id": self._seq, "method": method, "params": params}
        )
        self._proc.stdin.write((req + "\n").encode())
        await self._proc.stdin.drain()
        line = await self._proc.stdout.readline()
        resp = json.loads(line)
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp.get("result")

    async def list_tools(self) -> list[McpToolSpec]:
        result = await self._rpc("tools/list", {})
        tools: list[McpToolSpec] = []
        for t in result.get("tools", []):
            tools.append(
                McpToolSpec(
                    server_id=self._spec.id,
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        return result
