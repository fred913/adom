"""Long-term memory and compact snapshot types."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import ThreadId


class MemoryFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str


class MemoryPreference(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str


class MemoryTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    status: str = "open"  # "open" | "done"


class CompactSnapshot(BaseModel):
    thread_id: ThreadId
    summary: str
    facts: list[MemoryFact]
    preferences: list[MemoryPreference]
    tasks: list[MemoryTask]
    important_decisions: list[str]
    recent_capability_changes: list[str]
    compacted_at: datetime | None = None
    covers_up_to_event_id: str | None = None
