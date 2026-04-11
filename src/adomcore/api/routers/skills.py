"""Skills router."""

from fastapi import APIRouter, Request

from adomcore.api.schemas.skill import CreateSkillRequest, SkillResponse
from adomcore.domain.ids import SkillId

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
async def list_skills(request: Request) -> list[SkillResponse]:
    c = request.app.state.container
    return [
        SkillResponse(id=str(s.id), name=s.name, content=s.content, enabled=s.enabled)
        for s in c.skill_service.list_all()
    ]


@router.post("", response_model=SkillResponse)
async def create_skill(req: CreateSkillRequest, request: Request) -> SkillResponse:
    c = request.app.state.container
    s = await c.skill_service.add(SkillId(req.skill_id), req.name, req.content)
    return SkillResponse(
        id=str(s.id), name=s.name, content=s.content, enabled=s.enabled
    )
