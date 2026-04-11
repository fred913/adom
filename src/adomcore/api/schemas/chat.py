"""Chat schemas."""

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    text: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response_text: str
    thread_id: str
    steps: int
    tool_calls: list[dict[str, Any]] = []


class ChatStreamEvent(BaseModel):
    event: str
    data: dict[str, Any]
