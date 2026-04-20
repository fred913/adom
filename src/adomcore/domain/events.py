"""Event envelope for JSONL event streams."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import ThreadId
from adomcore.utils import StructuredValue


class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: str
    payload: dict[str, StructuredValue]


class EventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: str
    ts: datetime
    thread_id: ThreadId
    payload: dict[str, StructuredValue]
