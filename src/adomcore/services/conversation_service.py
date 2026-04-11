"""Conversation service — entry point from API into AgentRuntime."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from adomcore.domain.ids import ThreadId
from adomcore.domain.streaming import TurnStreamEvent

if TYPE_CHECKING:
    from adomcore.runtime.agent_runtime import AgentRuntime
    from adomcore.runtime.response_builder import TurnResult


class ConversationService:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def chat(self, text: str, thread_id: ThreadId | None = None) -> TurnResult:

        tid = thread_id or ThreadId("main")
        return await self._runtime.run_user_turn(tid, text)

    async def chat_stream(
        self, text: str, thread_id: ThreadId | None = None
    ) -> AsyncIterator[TurnStreamEvent]:
        tid = thread_id or ThreadId("main")
        async for event in self._runtime.run_user_turn_stream(tid, text):
            yield event
