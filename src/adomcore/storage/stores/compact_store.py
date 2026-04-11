"""Compact store — data/threads/<id>/compact.json5."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.ids import ThreadId
from adomcore.domain.memory import CompactSnapshot
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class CompactStore:
    _adapter = TypeAdapter(CompactSnapshot)

    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    def load(self, tid: ThreadId) -> CompactSnapshot | None:
        data: dict[str, Any] | None = self._json5.read(self._paths.thread_compact(tid))
        if data is None:
            return None
        return self._adapter.validate_python(data)

    async def save(self, snapshot: CompactSnapshot) -> None:
        data: dict[str, Any] = snapshot.model_dump(mode="json")
        await self._json5.write(self._paths.thread_compact(snapshot.thread_id), data)
