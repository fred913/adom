"""AgentEngine protocol — abstraction over LLM agent frameworks."""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from adomcore.domain.actions import AgentDecision
from adomcore.domain.streaming import EngineEvent


@runtime_checkable
class AgentEngine(Protocol):
    async def decide(self, context: dict[str, Any]) -> AgentDecision: ...

    def stream_decide(self, context: dict[str, Any]) -> AsyncIterator[EngineEvent]: ...

    async def summarise(self, prompt: str) -> dict[str, Any]: ...
