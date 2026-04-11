"""MCP schemas."""

from pydantic import BaseModel


class AddMcpServerRequest(BaseModel):
    server_id: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


class McpServerResponse(BaseModel):
    id: str
    command: str
    enabled: bool
