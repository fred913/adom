"""Runtime store — boot.json5 + health.json5."""

from datetime import datetime
from typing import Any

from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class RuntimeStore:
    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    async def write_boot(self, pid: int, started_at: datetime) -> None:
        await self._json5.write(
            self._paths.runtime_boot,
            {"pid": pid, "started_at": started_at.isoformat()},
        )

    async def write_health(self, data: dict[str, Any]) -> None:
        await self._json5.write(self._paths.runtime_health, data)

    def read_health(self) -> dict[str, Any] | None:
        return self._json5.read(self._paths.runtime_health)
