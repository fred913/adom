"""Skill store — data/agent/skills.json5 (single file, all skills)."""

from typing import Any

from pydantic import TypeAdapter

from adomcore.domain.skills import SkillSpec
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver


class SkillStore:
    _adapter = TypeAdapter(list[SkillSpec])

    def __init__(self, paths: PathResolver, json5: Json5Store) -> None:
        self._paths = paths
        self._json5 = json5

    def load_all(self) -> list[SkillSpec]:
        data: list[dict[str, Any]] | None = self._json5.read(self._paths.skills_file)
        if data is None:
            return []
        return self._adapter.validate_python(data)

    async def save_all(self, skills: list[SkillSpec]) -> None:
        data = [skill.model_dump(mode="json") for skill in skills]
        await self._json5.write(self._paths.skills_file, data)
