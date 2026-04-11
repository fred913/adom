"""Cron schemas."""

from pydantic import BaseModel


class CreateCronJobRequest(BaseModel):
    job_id: str
    cron_expr: str
    instruction_text: str
    target_thread_id: str = "main"


class CronJobResponse(BaseModel):
    job_id: str
    cron_expr: str
    instruction_text: str
    enabled: bool
