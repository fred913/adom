"""AppPaths — single source of truth for all file paths."""

from pathlib import Path

from pydantic import Field
from pydantic.dataclasses import dataclass

from adomcore.storage.path_resolver import PathResolver


@dataclass(frozen=True, config={"arbitrary_types_allowed": True})
class AppPaths:
    # def __init__(self, root: Path) -> None:
    #     self.root = root
    #     self.resolver = PathResolver(root)
    #     self.config_dir = Path("config")
    #     self.logs_dir = Path("logs")
    root: Path
    resolver: PathResolver = Field(init=False)
    config_dir: Path = Field(default=Path("config"), init=False)
    logs_dir: Path = Field(default=Path("logs"), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolver", PathResolver(self.root))


class PathFactory:
    @staticmethod
    def from_settings(storage_root: str) -> AppPaths:
        return AppPaths(Path(storage_root))
