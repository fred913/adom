"""MCP store — servers.json5 + discovered_tools.json5."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.ids import McpServerId
from adomcore.domain.mcp import McpServerSpec, McpToolSpec
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class McpStore:
    _server_adapter = TypeAdapter(list[McpServerSpec])
    _tool_adapter = TypeAdapter(list[McpToolSpec])

    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    def load_servers(self) -> list[McpServerSpec]:
        data: list[dict[str, Any]] | None = self._json5.read(self._paths.mcp_servers)
        if data is None:
            return []
        return self._server_adapter.validate_python(data)

    async def save_servers(self, servers: list[McpServerSpec]) -> None:
        data = [server.model_dump(mode="json") for server in servers]
        await self._json5.write(self._paths.mcp_servers, data)

    def load_tools(self, sid: McpServerId | None = None) -> list[McpToolSpec]:
        path = self._paths.mcp_discovered_tools(sid)
        data: list[dict[str, Any]] | None = self._json5.read(path)
        if data is None:
            return []
        return self._tool_adapter.validate_python(data)

    async def save_tools(
        self, tools: list[McpToolSpec], sid: McpServerId | None = None
    ) -> None:
        path = self._paths.mcp_discovered_tools(sid)
        data = [tool.model_dump(mode="json") for tool in tools]
        await self._json5.write(path, data)
