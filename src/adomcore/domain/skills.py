"""Skill specifications."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import SkillId


class SkillSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: SkillId
    name: str
    content: str
    enabled: bool = True
    created_at: datetime | None = None
