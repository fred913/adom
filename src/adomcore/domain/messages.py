"""Message types flowing through conversation threads."""

from datetime import datetime

from pydantic.dataclasses import dataclass

from adomcore.domain.ids import ThreadId


@dataclass(frozen=True)
class UserMessage:
    text: str
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class AssistantMessage:
    text: str
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class ToolCallMessage:
    function_name: str
    arguments: dict[str, object]
    call_id: str
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class ToolResultMessage:
    function_name: str
    call_id: str
    result: object
    is_error: bool
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class McpCallMessage:
    server_id: str
    tool_name: str
    arguments: dict[str, object]
    call_id: str
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class McpResultMessage:
    server_id: str
    tool_name: str
    call_id: str
    result: object
    is_error: bool
    thread_id: ThreadId
    ts: datetime


@dataclass(frozen=True)
class SystemEventMessage:
    event_kind: str
    detail: dict[str, object]
    thread_id: ThreadId
    ts: datetime


type ConversationMessage = (
    UserMessage
    | AssistantMessage
    | ToolCallMessage
    | ToolResultMessage
    | McpCallMessage
    | McpResultMessage
    | SystemEventMessage
)
