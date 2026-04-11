"""MCP router."""

from fastapi import APIRouter, Request

from adomcore.api.schemas.mcp import AddMcpServerRequest, McpServerResponse
from adomcore.domain.ids import McpServerId

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers", response_model=list[McpServerResponse])
async def list_servers(request: Request) -> list[McpServerResponse]:
    c = request.app.state.container
    return [
        McpServerResponse(id=str(s.id), command=s.command, enabled=s.enabled)
        for s in c.mcp_service.list_all()
    ]


@router.post("/servers", response_model=McpServerResponse)
async def add_server(req: AddMcpServerRequest, request: Request) -> McpServerResponse:
    c = request.app.state.container
    s = await c.mcp_service.add(
        McpServerId(req.server_id), req.command, req.args, req.env
    )
    return McpServerResponse(id=str(s.id), command=s.command, enabled=s.enabled)
