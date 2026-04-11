"""Atomic file writer — write to temp, then os.replace()."""

import os
import tempfile
from pathlib import Path


class AtomicWriter:
    """Write files atomically by writing to a temp file and then replacing."""

    @staticmethod
    def write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
        """Atomically write text content to *path*.

        Creates parent directories if they do not exist.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            # Clean up temp file on any failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def write_bytes(path: Path, content: bytes) -> None:
        """Atomically write binary content to *path*."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
