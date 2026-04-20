"""Application settings — loaded from config/config.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from adomcore.domain.models import ModelSpec
from adomcore.utils import require_json_object


def _empty_model_specs() -> list[ModelSpec]:
    return []


class ApiSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = []


class RuntimeSettings(BaseModel):
    max_loop_steps: int = 8
    auto_compact: bool = True
    compact_soft_ratio: float = 0.75
    compact_hard_ratio: float = 0.9
    recent_messages_window: int = 24


class StorageSettings(BaseModel):
    root_dir: str = "./data"


class SchedulerSettings(BaseModel):
    backend: str = "apscheduler"
    tick_seconds: int = 1


class PluginConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    def __getitem__(self, key: str) -> object:
        return getattr(self, key)


class PluginSettings(BaseModel):
    plugin_dirs: list[str] = Field(default_factory=list)
    config: dict[str, PluginConfig] = Field(default_factory=dict)


class AppSettings(BaseModel):
    timezone: str = "Asia/Shanghai"
    default_thread_id: str = "main"
    default_model_id: str = "main"
    api: ApiSettings = ApiSettings()
    runtime: RuntimeSettings = RuntimeSettings()
    storage: StorageSettings = StorageSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    plugins: PluginSettings = PluginSettings()
    models: list[ModelSpec] = Field(default_factory=_empty_model_specs)

    @classmethod
    def load(cls, config_path: Path = Path("config.yaml")) -> AppSettings:
        if not config_path.exists():
            return cls()
        with open(config_path) as f:
            data = require_json_object(yaml.safe_load(f) or {})
        return cls.model_validate(data)
