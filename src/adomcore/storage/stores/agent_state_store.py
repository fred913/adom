"""Agent state store — reads/writes data/agent/state.json5."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.agent import AgentState
from adomcore.domain.ids import ThreadId
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class AgentStateStore:
    _adapter = TypeAdapter(AgentState)

    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    def load(self) -> AgentState:
        data: dict[str, Any] | None = self._json5.read(self._paths.agent_state)
        if data is None:
            return AgentState(
                active_model_id="main",
                enabled_plugin_ids=[],
                enabled_skill_ids=[],
                enabled_mcp_server_ids=[],
                default_thread_id=ThreadId("main"),
            )
        return self._adapter.validate_python(data)

    async def save(self, state: AgentState) -> None:
        await self._json5.write(self._paths.agent_state, state.model_dump(mode="json"))
