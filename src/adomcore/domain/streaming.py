"""Streaming event models for engine and runtime layers."""

from enum import StrEnum
from typing import Literal

from pydantic.dataclasses import dataclass

from adomcore.domain.actions import AgentDecision
from adomcore.utils import StructuredValue


@dataclass(frozen=True)
class EngineTextDeltaEvent:
    kind: Literal["assistant_text_delta"]
    text: str


@dataclass(frozen=True)
class EngineToolCallDeltaEvent:
    kind: Literal["tool_call_delta"]
    call_id: str
    tool_name: str | None = None
    arguments_delta: str = ""


@dataclass(frozen=True)
class EngineDecisionEvent:
    kind: Literal["decision"]
    decision: AgentDecision


type EngineEvent = EngineTextDeltaEvent | EngineToolCallDeltaEvent | EngineDecisionEvent


class TurnStreamEventType(StrEnum):
    ASSISTANT_TEXT_DELTA = "assistant_text_delta"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_FINISHED = "tool_call_finished"
    TOOL_PROGRESS = "tool_progress"
    TOOL_PROGRESS_SUMMARY = "tool_progress_summary"
    TOOL_RESULT = "tool_result"
    ASSISTANT_TEXT_DONE = "assistant_text_done"
    TURN_DONE = "turn_done"


@dataclass(frozen=True)
class TurnStreamEvent:
    event: TurnStreamEventType
    data: dict[str, StructuredValue]
