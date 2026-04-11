"""YAML store — read/write YAML config files."""

from pathlib import Path
from typing import Any

import yaml

from adomcore.storage.atomic_writer import AtomicWriter


class YamlStore:
    @staticmethod
    def read(path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def write(path: Path, data: Any) -> None:
        AtomicWriter.write_text(path, yaml.dump(data, allow_unicode=True))
