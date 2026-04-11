"""In-process file lock manager for single-instance concurrency control."""

import asyncio
from pathlib import Path


class FileLockManager:
    """Manages asyncio locks keyed by canonical file paths.

    Since adomcore is single-instance, file-system-level locks are unnecessary.
    In-process ``asyncio.Lock`` instances protect against concurrent FastAPI
    request handlers and scheduler callbacks mutating the same file.
    """

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def get(self, path: Path) -> asyncio.Lock:
        """Return the lock associated with *path*, creating it if needed."""
        key = str(path.resolve())
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def remove(self, path: Path) -> None:
        """Remove the lock for *path* if present."""
        key = str(path.resolve())
        self._locks.pop(key, None)
