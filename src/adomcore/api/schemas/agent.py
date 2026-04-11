"""Agent schemas."""

from pydantic import BaseModel


class AgentStateResponse(BaseModel):
    active_model_id: str
    enabled_plugin_ids: list[str]
    enabled_skill_ids: list[str]
    enabled_mcp_server_ids: list[str]
    default_thread_id: str
