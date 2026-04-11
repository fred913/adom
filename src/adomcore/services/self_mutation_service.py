"""Self-mutation service — single entry point for agent self-modification."""

from adomcore.domain.ids import McpServerId, SkillId
from adomcore.services.agent_service import AgentService
from adomcore.services.mcp_service import McpService
from adomcore.services.skill_service import SkillService


class SelfMutationService:
    def __init__(
        self,
        agent_svc: AgentService,
        skill_svc: SkillService,
        mcp_svc: McpService,
    ) -> None:
        self._agent = agent_svc
        self._skills = skill_svc
        self._mcp = mcp_svc

    async def add_skill(self, skill_id: SkillId, name: str, content: str) -> None:
        await self._skills.add(skill_id, name, content)
        state = self._agent.load()
        if skill_id not in state.enabled_skill_ids:
            await self._agent.save(
                state.model_copy(
                    update={"enabled_skill_ids": [*state.enabled_skill_ids, skill_id]}
                )
            )

    async def enable_skill(self, skill_id: SkillId) -> None:
        await self._skills.enable(skill_id)
        state = self._agent.load()
        if skill_id not in state.enabled_skill_ids:
            await self._agent.save(
                state.model_copy(
                    update={"enabled_skill_ids": [*state.enabled_skill_ids, skill_id]}
                )
            )

    async def disable_skill(self, skill_id: SkillId) -> None:
        await self._skills.disable(skill_id)
        state = self._agent.load()
        if skill_id in state.enabled_skill_ids:
            await self._agent.save(
                state.model_copy(
                    update={
                        "enabled_skill_ids": [
                            enabled_id
                            for enabled_id in state.enabled_skill_ids
                            if enabled_id != skill_id
                        ]
                    }
                )
            )

    async def add_mcp_server(
        self,
        sid: McpServerId,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> None:
        await self._mcp.add(sid, command, args, env)
        state = self._agent.load()
        if sid not in state.enabled_mcp_server_ids:
            await self._agent.save(
                state.model_copy(
                    update={
                        "enabled_mcp_server_ids": [
                            *state.enabled_mcp_server_ids,
                            sid,
                        ]
                    }
                )
            )

    async def enable_mcp_server(self, sid: McpServerId) -> None:
        await self._mcp.enable(sid)
        state = self._agent.load()
        if sid not in state.enabled_mcp_server_ids:
            await self._agent.save(
                state.model_copy(
                    update={
                        "enabled_mcp_server_ids": [
                            *state.enabled_mcp_server_ids,
                            sid,
                        ]
                    }
                )
            )

    async def disable_mcp_server(self, sid: McpServerId) -> None:
        await self._mcp.disable(sid)
        state = self._agent.load()
        if sid in state.enabled_mcp_server_ids:
            await self._agent.save(
                state.model_copy(
                    update={
                        "enabled_mcp_server_ids": [
                            enabled_id
                            for enabled_id in state.enabled_mcp_server_ids
                            if enabled_id != sid
                        ]
                    }
                )
            )

    async def switch_model(self, model_id: str) -> None:
        state = self._agent.load()
        await self._agent.save(state.model_copy(update={"active_model_id": model_id}))
