"""MCP schemas."""

from pydantic import BaseModel, Field


class AddMcpServerRequest(BaseModel):
    server_id: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class McpServerResponse(BaseModel):
    id: str
    command: str
    enabled: bool
