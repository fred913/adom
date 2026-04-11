"""Cron store — jobs.json5 + history.jsonl."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.cron import CronRunRecord, ScheduledInstruction
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.jsonl_store import JsonlStore
from adomcore.storage.path_resolver import PathResolver


class CronStore:
    _jobs_adapter = TypeAdapter(list[ScheduledInstruction])

    def __init__(
        self, paths: PathResolver, json5: Json5Store, jsonl: JsonlStore
    ) -> None:
        self._paths = paths
        self._json5 = json5
        self._jsonl = jsonl

    def load_jobs(self) -> list[ScheduledInstruction]:
        data: list[dict[str, Any]] | None = self._json5.read(self._paths.cron_jobs)
        if data is None:
            return []
        return self._jobs_adapter.validate_python(data)

    async def save_jobs(self, jobs: list[ScheduledInstruction]) -> None:
        data = [job.model_dump(mode="json") for job in jobs]
        await self._json5.write(self._paths.cron_jobs, data)

    async def append_run_record(self, record: CronRunRecord) -> None:
        row: dict[str, Any] = record.model_dump(mode="json")
        await self._jsonl.append(self._paths.cron_history, row)
