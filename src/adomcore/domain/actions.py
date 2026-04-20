"""Agent decision actions — the union type that runtime routes."""

from pydantic.dataclasses import dataclass

from adomcore.domain.ids import CronJobId, McpServerId, PluginId, SkillId
from adomcore.utils import StructuredValue


@dataclass(frozen=True)
class RespondAction:
    text: str


@dataclass(frozen=True)
class CallFunctionAction:
    function_name: str
    arguments: dict[str, StructuredValue]
    call_id: str


@dataclass(frozen=True)
class CallMcpToolAction:
    server_id: McpServerId
    tool_name: str
    arguments: dict[str, StructuredValue]
    call_id: str


@dataclass(frozen=True)
class AddSkillAction:
    skill_id: SkillId
    name: str
    content: str


@dataclass(frozen=True)
class EnableSkillAction:
    skill_id: SkillId


@dataclass(frozen=True)
class DisableSkillAction:
    skill_id: SkillId


@dataclass(frozen=True)
class AddMcpServerAction:
    server_id: McpServerId
    command: str
    args: list[str]
    env: dict[str, str]


@dataclass(frozen=True)
class EnableMcpServerAction:
    server_id: McpServerId


@dataclass(frozen=True)
class DisableMcpServerAction:
    server_id: McpServerId


@dataclass(frozen=True)
class InstallPluginAction:
    plugin_id: PluginId
    source: str


@dataclass(frozen=True)
class EnablePluginAction:
    plugin_id: PluginId


@dataclass(frozen=True)
class DisablePluginAction:
    plugin_id: PluginId


@dataclass(frozen=True)
class SwitchModelAction:
    model_id: str


@dataclass(frozen=True)
class CreateCronJobAction:
    job_id: CronJobId
    cron_expr: str
    instruction: str


@dataclass(frozen=True)
class RemoveCronJobAction:
    job_id: CronJobId


type AgentAction = (
    RespondAction
    | CallFunctionAction
    | CallMcpToolAction
    | AddSkillAction
    | EnableSkillAction
    | DisableSkillAction
    | AddMcpServerAction
    | EnableMcpServerAction
    | DisableMcpServerAction
    | InstallPluginAction
    | EnablePluginAction
    | DisablePluginAction
    | SwitchModelAction
    | CreateCronJobAction
    | RemoveCronJobAction
)


@dataclass(frozen=True)
class AgentDecision:
    actions: list[AgentAction]
    reasoning: str | None = None
