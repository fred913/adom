"""ActionRouter — route AgentDecision actions to executors."""

from datetime import UTC
from typing import Any, cast

from pydantic.dataclasses import dataclass

from adomcore.domain.actions import (
    AgentAction,
    CallFunctionAction,
    CallMcpToolAction,
    RespondAction,
)


@dataclass
class ActionExecutionResult:
    action: AgentAction
    result: Any
    is_error: bool = False
    error_detail: str | None = None


class ActionRouter:
    def __init__(
        self,
        tool_executor: object,
        mcp_session_manager: object,
        self_mutation_service: object,
        scheduler_service: object,
    ) -> None:
        self._tools = tool_executor
        self._mcp = mcp_session_manager
        self._mutation = self_mutation_service
        self._scheduler = scheduler_service

    async def route(self, action: AgentAction) -> ActionExecutionResult:
        try:
            result = await self._dispatch(action)
            return ActionExecutionResult(action=action, result=result)
        except Exception as exc:
            return ActionExecutionResult(
                action=action, result=None, is_error=True, error_detail=str(exc)
            )

    async def _dispatch(self, action: AgentAction) -> Any:
        from adomcore.domain.actions import (
            AddMcpServerAction,
            AddSkillAction,
            CreateCronJobAction,
            DisableMcpServerAction,
            DisableSkillAction,
            EnableMcpServerAction,
            EnableSkillAction,
            RemoveCronJobAction,
            SwitchModelAction,
        )
        from adomcore.services.mcp_session_manager import McpSessionManager
        from adomcore.services.scheduler_service import SchedulerService
        from adomcore.services.self_mutation_service import SelfMutationService
        from adomcore.services.tool_executor import ToolExecutor

        assert isinstance(self._tools, ToolExecutor)
        assert isinstance(self._mcp, McpSessionManager)
        assert isinstance(self._mutation, SelfMutationService)
        assert isinstance(self._scheduler, SchedulerService)

        if isinstance(action, RespondAction):
            return action.text
        if isinstance(action, CallFunctionAction):
            return await self._tools.execute(action.function_name, action.arguments)
        if isinstance(action, CallMcpToolAction):
            session = self._mcp.get_session(action.server_id)
            from adomcore.integrations.mcp.stdio_client import McpClientProtocol

            if session is None:
                raise ValueError(f"MCP server not connected: {action.server_id}")
            return await cast(McpClientProtocol, session).call_tool(
                action.tool_name, action.arguments
            )
        if isinstance(action, AddSkillAction):
            await self._mutation.add_skill(action.skill_id, action.name, action.content)
            return "skill added"
        if isinstance(action, EnableSkillAction):
            await self._mutation.enable_skill(action.skill_id)
            return "skill enabled"
        if isinstance(action, DisableSkillAction):
            await self._mutation.disable_skill(action.skill_id)
            return "skill disabled"
        if isinstance(action, AddMcpServerAction):
            await self._mutation.add_mcp_server(
                action.server_id, action.command, action.args, action.env
            )
            return "mcp server added"
        if isinstance(action, EnableMcpServerAction):
            await self._mutation.enable_mcp_server(action.server_id)
            return "mcp server enabled"
        if isinstance(action, DisableMcpServerAction):
            await self._mutation.disable_mcp_server(action.server_id)
            return "mcp server disabled"
        if isinstance(action, SwitchModelAction):
            await self._mutation.switch_model(action.model_id)
            return "model switched"
        if isinstance(action, CreateCronJobAction):
            from datetime import datetime

            from adomcore.domain.cron import CronTriggerSpec, ScheduledInstruction
            from adomcore.domain.ids import ThreadId

            job = ScheduledInstruction(
                job_id=action.job_id,
                trigger=CronTriggerSpec(cron_expr=action.cron_expr),
                instruction_text=action.instruction,
                target_thread_id=ThreadId("main"),
                enabled=True,
                created_at=datetime.now(UTC),
            )
            await self._scheduler.add_job(job)
            return "cron job created"
        if isinstance(action, RemoveCronJobAction):
            await self._scheduler.remove_job(action.job_id)
            return "cron job removed"
        raise ValueError(f"Unknown action type: {type(action)}")
