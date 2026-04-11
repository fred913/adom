"""APScheduler backend — no DB job store; jobs rebuilt from CronStore on startup."""

from collections.abc import Awaitable, Callable
from importlib import import_module
from typing import Any

from loguru import logger


class APSchedulerBackend:
    def __init__(self) -> None:
        self._scheduler: object | None = None

    def _get_scheduler(self) -> Any:
        if self._scheduler is None:
            scheduler_class = self._asyncio_scheduler_class()
            self._scheduler = scheduler_class()
        return self._scheduler

    def _asyncio_scheduler_class(self) -> Any:
        module = import_module("apscheduler.schedulers.asyncio")
        return getattr(module, "AsyncIOScheduler")

    def _cron_trigger_class(self) -> Any:
        module = import_module("apscheduler.triggers.cron")
        return getattr(module, "CronTrigger")

    async def start(self) -> None:
        sched = self._get_scheduler()
        assert isinstance(sched, self._asyncio_scheduler_class())
        sched.start()
        logger.info("APScheduler started")

    async def stop(self) -> None:
        sched = self._get_scheduler()
        assert isinstance(sched, self._asyncio_scheduler_class())
        if sched.running:
            sched.shutdown(wait=False)
        logger.info("APScheduler stopped")

    async def add_cron_job(
        self,
        job_id: str,
        cron_expr: str,
        callback: Callable[[], Awaitable[None]],
    ) -> None:
        sched = self._get_scheduler()
        assert isinstance(sched, self._asyncio_scheduler_class())
        parts = cron_expr.split()
        cron_trigger = self._cron_trigger_class()
        trigger = cron_trigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )
        sched.add_job(callback, trigger=trigger, id=job_id, replace_existing=True)
        logger.debug("Scheduled cron job: {} ({})", job_id, cron_expr)

    async def remove_job(self, job_id: str) -> None:
        sched = self._get_scheduler()
        assert isinstance(sched, self._asyncio_scheduler_class())
        try:
            sched.remove_job(job_id)
        except Exception:
            pass
