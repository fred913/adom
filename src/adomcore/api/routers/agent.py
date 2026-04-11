"""Agent router."""

from fastapi import APIRouter, Request

from adomcore.api.schemas.agent import AgentStateResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/state", response_model=AgentStateResponse)
async def get_state(request: Request) -> AgentStateResponse:
    c = request.app.state.container
    state = c.agent_service.load()
    return AgentStateResponse(
        active_model_id=state.active_model_id,
        enabled_plugin_ids=[str(p) for p in state.enabled_plugin_ids],
        enabled_skill_ids=[str(s) for s in state.enabled_skill_ids],
        enabled_mcp_server_ids=[str(m) for m in state.enabled_mcp_server_ids],
        default_thread_id=str(state.default_thread_id),
    )
