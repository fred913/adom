from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import cast

from adomcore.domain.cron import CronRunRecord, CronTriggerSpec, ScheduledInstruction
from adomcore.domain.ids import CronJobId, ThreadId
from adomcore.integrations.scheduler.backend_protocol import SchedulerBackend
from adomcore.services.scheduler_service import SchedulerService
from adomcore.storage.stores.cron_store import CronStore


class FakeCronStore:
    def __init__(self, jobs: list[ScheduledInstruction] | None = None) -> None:
        self.jobs = list(jobs or [])
        self.saved_jobs: list[ScheduledInstruction] | None = None
        self.records: list[CronRunRecord] = []

    def load_jobs(self) -> list[ScheduledInstruction]:
        return list(self.jobs)

    async def save_jobs(self, jobs: list[ScheduledInstruction]) -> None:
        self.jobs = list(jobs)
        self.saved_jobs = list(jobs)

    async def append_run_record(self, record: CronRunRecord) -> None:
        self.records.append(record)


class FakeBackend(SchedulerBackend):
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.added_jobs: list[tuple[str, str, Callable[[], Awaitable[None]]]] = []
        self.removed_jobs: list[str] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def add_cron_job(
        self, job_id: str, cron_expr: str, callback: Callable[[], Awaitable[None]]
    ) -> None:
        self.added_jobs.append((job_id, cron_expr, callback))

    async def remove_job(self, job_id: str) -> None:
        self.removed_jobs.append(job_id)


def _job(job_id: str, enabled: bool = True) -> ScheduledInstruction:
    return ScheduledInstruction(
        job_id=CronJobId(job_id),
        trigger=CronTriggerSpec(cron_expr="* * * * *"),
        instruction_text="do thing",
        target_thread_id=ThreadId("thread-1"),
        enabled=enabled,
    )


async def test_start_schedules_only_enabled_jobs_and_dispatches_callback() -> None:
    store = FakeCronStore([_job("job-enabled"), _job("job-disabled", enabled=False)])
    backend = FakeBackend()
    fired: list[CronJobId] = []

    service = SchedulerService(cast(CronStore, store))
    service.set_backend(backend)

    async def dispatch(job_id: CronJobId) -> None:
        fired.append(job_id)

    service.set_dispatch_callback(dispatch)

    await service.start()

    assert backend.started is True
    assert [job_id for job_id, _, _ in backend.added_jobs] == ["job-enabled"]

    callback = backend.added_jobs[0][2]
    await callback()
    assert fired == [CronJobId("job-enabled")]


async def test_add_remove_and_record_run_delegate_to_store_and_backend() -> None:
    store = FakeCronStore()
    backend = FakeBackend()
    service = SchedulerService(cast(CronStore, store))
    service.set_backend(backend)

    job = _job("job-1")
    await service.add_job(job)

    assert store.saved_jobs == [job]
    assert backend.added_jobs[0][0] == "job-1"

    await service.remove_job(CronJobId("job-1"))

    assert store.saved_jobs == []
    assert backend.removed_jobs == ["job-1"]

    record = CronRunRecord(job_id=CronJobId("job-1"), fired_at=datetime.now())
    await service.record_run(record)
    assert store.records == [record]
