"""Chat schemas."""

from pydantic import BaseModel, Field

from adomcore.runtime.response_builder import ToolCallRecord
from adomcore.utils import StructuredValue


class ChatRequest(BaseModel):
    text: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response_text: str
    thread_id: str
    steps: int
    tool_calls: list[ToolCallRecord] = Field(default_factory=lambda: [])


class ChatStreamEvent(BaseModel):
    event: str
    data: dict[str, StructuredValue]
