"""Agent service — read/write AgentState."""

from adomcore.domain.agent import AgentState
from adomcore.storage.stores.agent_state_store import AgentStateStore


class AgentService:
    def __init__(self, store: AgentStateStore) -> None:
        self._store = store
        self._state: AgentState | None = None

    def load(self) -> AgentState:
        if self._state is None:
            self._state = self._store.load()
        return self._state

    async def save(self, state: AgentState) -> None:
        self._state = state
        await self._store.save(state)
