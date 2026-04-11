"""Thread store — events.jsonl + meta.json5 per thread."""

from typing import Any

from adomcore.domain.events import EventEnvelope
from adomcore.domain.ids import ThreadId
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.jsonl_store import JsonlStore
from adomcore.storage.path_resolver import PathResolver


class ThreadStore:
    def __init__(
        self,
        paths: PathResolver,
        json5: Json5Store,
        jsonl: JsonlStore,
    ) -> None:
        self._paths = paths
        self._json5 = json5
        self._jsonl = jsonl

    async def append_event(self, envelope: EventEnvelope) -> None:
        path = self._paths.thread_events(envelope.thread_id)
        record: dict[str, Any] = envelope.model_dump(mode="json")
        await self._jsonl.append(path, record)

    def read_events(
        self,
        tid: ThreadId,
        *,
        tail: int | None = None,
    ) -> list[dict[str, Any]]:
        path = self._paths.thread_events(tid)
        if tail is not None:
            return self._jsonl.read_tail(path, tail)
        return self._jsonl.read_all(path)

    def read_meta(self, tid: ThreadId) -> dict[str, Any] | None:
        return self._json5.read(self._paths.thread_meta(tid))

    async def write_meta(self, tid: ThreadId, meta: dict[str, Any]) -> None:
        await self._json5.write(self._paths.thread_meta(tid), meta)

    def ensure_thread_dir(self, tid: ThreadId) -> None:
        self._paths.thread_dir(tid).mkdir(parents=True, exist_ok=True)
