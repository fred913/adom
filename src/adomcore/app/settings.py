"""Application settings — loaded from config/config.yaml."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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


class PluginSettings(BaseModel):
    plugin_dirs: list[str] = Field(default_factory=list)
    config: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AppSettings(BaseModel):
    timezone: str = "Asia/Shanghai"
    default_thread_id: str = "main"
    default_model_id: str = "main"
    api: ApiSettings = ApiSettings()
    runtime: RuntimeSettings = RuntimeSettings()
    storage: StorageSettings = StorageSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    plugins: PluginSettings = PluginSettings()
    models: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def load(cls, config_path: Path = Path("config.yaml")) -> AppSettings:
        if not config_path.exists():
            return cls()
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls.model_validate(data)
