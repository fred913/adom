"""JSONL store — append-only event stream files."""

import json
from pathlib import Path
from typing import Any

import aiofiles

from adomcore.storage.file_lock import FileLockManager

_lock_mgr = FileLockManager()


class JsonlStore:
    def __init__(self, lock_mgr: FileLockManager | None = None) -> None:
        self._locks = lock_mgr or _lock_mgr

    def read_all(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        lines: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return lines

    def read_tail(self, path: Path, n: int) -> list[dict[str, Any]]:
        return self.read_all(path)[-n:]

    async def append(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        async with self._locks.get(path):
            async with aiofiles.open(path, "a", encoding="utf-8") as f:
                await f.write(line)
