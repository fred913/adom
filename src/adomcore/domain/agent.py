"""Agent profile and runtime state."""

from pydantic import BaseModel, ConfigDict

from adomcore.domain.ids import McpServerId, PluginId, SkillId, ThreadId


class AgentProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "adomcore"
    description: str = ""
    system_prompt_preamble: str = ""


class AgentState(BaseModel):
    active_model_id: str
    enabled_plugin_ids: list[PluginId]
    enabled_skill_ids: list[SkillId]
    enabled_mcp_server_ids: list[McpServerId]
    default_thread_id: ThreadId
