"""MCP server and tool specifications."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import McpServerId


class McpServerSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: McpServerId
    command: str
    args: list[str]
    env: dict[str, str]
    enabled: bool = True


class McpToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    server_id: McpServerId
    name: str
    description: str
    input_schema: dict[str, Any]
