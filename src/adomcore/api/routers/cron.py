"""Cron router."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from adomcore.api.schemas.cron import CreateCronJobRequest, CronJobResponse
from adomcore.domain.cron import CronTriggerSpec, ScheduledInstruction
from adomcore.domain.ids import CronJobId, ThreadId

router = APIRouter(prefix="/cron", tags=["cron"])


@router.get("/jobs", response_model=list[CronJobResponse])
async def list_jobs(request: Request) -> list[CronJobResponse]:
    c = request.app.state.container
    return [
        CronJobResponse(
            job_id=str(j.job_id),
            cron_expr=j.trigger.cron_expr,
            instruction_text=j.instruction_text,
            enabled=j.enabled,
        )
        for j in c.scheduler_service.list_jobs()
    ]


@router.post("/jobs", response_model=CronJobResponse)
async def create_job(req: CreateCronJobRequest, request: Request) -> CronJobResponse:
    c = request.app.state.container
    job = ScheduledInstruction(
        job_id=CronJobId(req.job_id),
        trigger=CronTriggerSpec(cron_expr=req.cron_expr),
        instruction_text=req.instruction_text,
        target_thread_id=ThreadId(req.target_thread_id),
        enabled=True,
        created_at=datetime.now(UTC),
    )
    await c.scheduler_service.add_job(job)
    return CronJobResponse(
        job_id=str(job.job_id),
        cron_expr=job.trigger.cron_expr,
        instruction_text=job.instruction_text,
        enabled=job.enabled,
    )
