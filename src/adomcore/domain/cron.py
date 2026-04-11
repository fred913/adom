"""Cron job domain types."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import CronJobId, ThreadId


class CronTriggerSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    cron_expr: str


class ScheduledInstruction(BaseModel):
    job_id: CronJobId
    trigger: CronTriggerSpec
    instruction_text: str
    target_thread_id: ThreadId
    enabled: bool = True
    created_at: datetime | None = None
    next_run_at: datetime | None = None


class CronRunRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: CronJobId
    fired_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
