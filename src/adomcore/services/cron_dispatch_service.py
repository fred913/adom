"""Cron dispatch service — fires timer turns into AgentRuntime."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from adomcore.domain.cron import CronRunRecord
from adomcore.domain.ids import CronJobId
from adomcore.services.scheduler_service import SchedulerService

if TYPE_CHECKING:
    from adomcore.runtime.agent_runtime import AgentRuntime


class CronDispatchService:
    def __init__(self, scheduler: SchedulerService, runtime: AgentRuntime) -> None:
        self._scheduler = scheduler
        self._runtime = runtime

    async def dispatch(self, job_id: CronJobId) -> None:
        jobs = {j.job_id: j for j in self._scheduler.list_jobs()}
        job = jobs.get(job_id)
        if job is None or not job.enabled:
            return

        fired_at = datetime.now(UTC)
        error: str | None = None
        try:
            await self._runtime.run_timer_turn(
                thread_id=job.target_thread_id,
                instruction_text=job.instruction_text,
                job_id=job_id,
            )
        except Exception as exc:
            error = str(exc)
            logger.exception("Cron job {} failed", job_id)

        record = CronRunRecord(
            job_id=job_id,
            fired_at=fired_at,
            completed_at=datetime.now(UTC),
            error=error,
        )
        await self._scheduler.record_run(record)
