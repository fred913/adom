"""Skill schemas."""

from pydantic import BaseModel


class CreateSkillRequest(BaseModel):
    skill_id: str
    name: str
    content: str


class SkillResponse(BaseModel):
    id: str
    name: str
    content: str
    enabled: bool
