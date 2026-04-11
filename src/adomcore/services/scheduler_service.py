"""Scheduler service — wrap SchedulerBackend, rebuild jobs from CronStore on startup."""

from collections.abc import Awaitable, Callable

from loguru import logger

from adomcore.domain.cron import CronRunRecord, ScheduledInstruction
from adomcore.domain.ids import CronJobId
from adomcore.integrations.scheduler.backend_protocol import SchedulerBackend
from adomcore.storage.stores.cron_store import CronStore


class SchedulerService:
    def __init__(self, store: CronStore) -> None:
        self._store = store
        self._backend: SchedulerBackend | None = None
        self._dispatch_callback: Callable[[CronJobId], Awaitable[None]] | None = None

    def set_backend(self, backend: SchedulerBackend) -> None:
        self._backend = backend

    def set_dispatch_callback(
        self, callback: Callable[[CronJobId], Awaitable[None]]
    ) -> None:
        self._dispatch_callback = callback

    async def start(self) -> None:
        if self._backend is None:
            return
        await self._backend.start()
        for job in self._store.load_jobs():
            if job.enabled:
                await self._schedule_job(job)
        logger.info("Scheduler started")

    async def stop(self) -> None:
        if self._backend is not None:
            await self._backend.stop()

    async def add_job(self, job: ScheduledInstruction) -> None:
        jobs = self._store.load_jobs()
        jobs.append(job)
        await self._store.save_jobs(jobs)
        if job.enabled:
            await self._schedule_job(job)

    async def remove_job(self, job_id: CronJobId) -> None:
        jobs = [j for j in self._store.load_jobs() if j.job_id != job_id]
        await self._store.save_jobs(jobs)
        if self._backend is not None:
            await self._backend.remove_job(str(job_id))

    async def _schedule_job(self, job: ScheduledInstruction) -> None:
        if self._backend is None:
            return

        async def _fire() -> None:
            if self._dispatch_callback is not None:
                await self._dispatch_callback(job.job_id)

        await self._backend.add_cron_job(
            job_id=str(job.job_id),
            cron_expr=job.trigger.cron_expr,
            callback=_fire,
        )

    async def record_run(self, record: CronRunRecord) -> None:
        await self._store.append_run_record(record)

    def list_jobs(self) -> list[ScheduledInstruction]:
        return self._store.load_jobs()
