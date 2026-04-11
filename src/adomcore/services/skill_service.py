"""Skill service — CRUD for SkillSpec via SkillStore."""

from datetime import UTC, datetime

from adomcore.domain.ids import SkillId
from adomcore.domain.skills import SkillSpec
from adomcore.storage.stores.skill_store import SkillStore


class SkillService:
    def __init__(self, store: SkillStore) -> None:
        self._store = store
        self._skills: dict[SkillId, SkillSpec] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            for s in self._store.load_all():
                self._skills[s.id] = s
            self._loaded = True

    def list_all(self) -> list[SkillSpec]:
        self._ensure_loaded()
        return list(self._skills.values())

    def list_enabled(self) -> list[SkillSpec]:
        self._ensure_loaded()
        return [s for s in self._skills.values() if s.enabled]

    def get(self, skill_id: SkillId) -> SkillSpec | None:
        self._ensure_loaded()
        return self._skills.get(skill_id)

    async def add(self, skill_id: SkillId, name: str, content: str) -> SkillSpec:
        self._ensure_loaded()
        spec = SkillSpec(
            id=skill_id,
            name=name,
            content=content,
            enabled=True,
            created_at=datetime.now(UTC),
        )
        self._skills[skill_id] = spec
        await self._store.save_all(list(self._skills.values()))
        return spec

    async def enable(self, skill_id: SkillId) -> None:
        self._ensure_loaded()
        old = self._skills.get(skill_id)
        if old is None:
            raise KeyError(f"Skill not found: {skill_id!r}")
        self._skills[skill_id] = old.model_copy(update={"enabled": True})
        await self._store.save_all(list(self._skills.values()))

    async def disable(self, skill_id: SkillId) -> None:
        self._ensure_loaded()
        old = self._skills.get(skill_id)
        if old is None:
            raise KeyError(f"Skill not found: {skill_id!r}")
        self._skills[skill_id] = old.model_copy(update={"enabled": False})
        await self._store.save_all(list(self._skills.values()))
