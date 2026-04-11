"""SchedulerBackend protocol."""

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class SchedulerBackend(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def add_cron_job(
        self,
        job_id: str,
        cron_expr: str,
        callback: Callable[[], Awaitable[None]],
    ) -> None: ...
    async def remove_job(self, job_id: str) -> None: ...
