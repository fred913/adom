"""MCP session manager — manage live stdio MCP connections."""

from loguru import logger

from adomcore.domain.ids import McpServerId
from adomcore.domain.mcp import McpServerSpec, McpToolSpec
from adomcore.storage.stores.mcp_store import McpStore


class McpSessionManager:
    """Manages active MCP server connections.

    Actual stdio session logic lives in integrations/mcp/.
    This service owns the lifecycle: connect, disconnect, refresh tools.
    """

    def __init__(self, store: McpStore) -> None:
        self._store = store
        # session objects keyed by server id — populated by integrations layer
        self._sessions: dict[McpServerId, object] = {}
        self._tools: dict[McpServerId, list[McpToolSpec]] = {}

    async def connect(self, spec: McpServerSpec) -> None:
        from adomcore.integrations.mcp.stdio_client import StdioMcpClient

        client = StdioMcpClient(spec)
        await client.start()
        self._sessions[spec.id] = client
        tools = await client.list_tools()
        self._tools[spec.id] = tools
        await self._store.save_tools(tools, spec.id)
        logger.info("MCP server connected: {}", spec.id)

    async def disconnect(self, sid: McpServerId) -> None:
        session = self._sessions.pop(sid, None)
        if session is not None:
            from adomcore.integrations.mcp.stdio_client import StdioMcpClient

            if isinstance(session, StdioMcpClient):
                await session.stop()
        self._tools.pop(sid, None)
        logger.info("MCP server disconnected: {}", sid)

    async def disconnect_all(self) -> None:
        for sid in list(self._sessions):
            await self.disconnect(sid)

    def get_tools(self, sid: McpServerId) -> list[McpToolSpec]:
        return self._tools.get(sid, [])

    def all_tools(self) -> list[McpToolSpec]:
        result: list[McpToolSpec] = []
        for tools in self._tools.values():
            result.extend(tools)
        return result

    def get_session(self, sid: McpServerId) -> object | None:
        return self._sessions.get(sid)
