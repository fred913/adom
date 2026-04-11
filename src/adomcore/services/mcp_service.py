"""MCP service — manage McpServerSpec configuration via McpStore."""

from adomcore.domain.ids import McpServerId
from adomcore.domain.mcp import McpServerSpec
from adomcore.storage.stores.mcp_store import McpStore


class McpService:
    def __init__(self, store: McpStore) -> None:
        self._store = store
        self._servers: dict[McpServerId, McpServerSpec] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            for s in self._store.load_servers():
                self._servers[s.id] = s
            self._loaded = True

    def list_all(self) -> list[McpServerSpec]:
        self._ensure_loaded()
        return list(self._servers.values())

    def list_enabled(self) -> list[McpServerSpec]:
        self._ensure_loaded()
        return [s for s in self._servers.values() if s.enabled]

    def get(self, sid: McpServerId) -> McpServerSpec | None:
        self._ensure_loaded()
        return self._servers.get(sid)

    async def add(
        self,
        sid: McpServerId,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> McpServerSpec:
        self._ensure_loaded()
        spec = McpServerSpec(id=sid, command=command, args=args, env=env, enabled=True)
        self._servers[sid] = spec
        await self._store.save_servers(list(self._servers.values()))
        return spec

    async def enable(self, sid: McpServerId) -> None:
        self._ensure_loaded()
        old = self._servers.get(sid)
        if old is None:
            raise KeyError(f"MCP server not found: {sid!r}")
        self._servers[sid] = old.model_copy(update={"enabled": True})
        await self._store.save_servers(list(self._servers.values()))

    async def disable(self, sid: McpServerId) -> None:
        self._ensure_loaded()
        old = self._servers.get(sid)
        if old is None:
            raise KeyError(f"MCP server not found: {sid!r}")
        self._servers[sid] = old.model_copy(update={"enabled": False})
        await self._store.save_servers(list(self._servers.values()))
