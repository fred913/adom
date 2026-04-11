"""JSON5 store — read/write current-state snapshot files."""

import json
from pathlib import Path
from typing import Any

from adomcore.storage.atomic_writer import AtomicWriter
from adomcore.storage.file_lock import FileLockManager

_lock_mgr = FileLockManager()


class Json5Store:
    def __init__(self, lock_mgr: FileLockManager | None = None) -> None:
        self._locks = lock_mgr or _lock_mgr

    def read(self, path: Path) -> Any:
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    async def write(self, path: Path, data: Any) -> None:
        text = json.dumps(data, indent=2)
        async with self._locks.get(path):
            AtomicWriter.write_text(path, text)
