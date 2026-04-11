"""PluginContext — restricted interface exposed to plugins."""

from collections.abc import Callable
from typing import Any

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import McpServerId, SkillId
from adomcore.services.capability_registry import CapabilityRegistry


class PluginContext:
    def __init__(
        self,
        registry: CapabilityRegistry,
        self_mutation_service: object | None = None,
    ) -> None:
        self._registry = registry
        self._self_mutation = self_mutation_service

    def register_function(
        self, spec: FunctionSpec, handler: Callable[..., Any]
    ) -> None:
        self._registry.register(spec, handler)

    async def register_skill(self, skill_id: str, name: str, content: str) -> None:
        from adomcore.services.self_mutation_service import SelfMutationService

        if not isinstance(self._self_mutation, SelfMutationService):
            raise RuntimeError("PluginContext is not configured for skill registration")
        await self._self_mutation.add_skill(SkillId(skill_id), name, content)

    async def register_mcp_server(
        self,
        server_id: str,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> None:
        from adomcore.services.self_mutation_service import SelfMutationService

        if not isinstance(self._self_mutation, SelfMutationService):
            raise RuntimeError("PluginContext is not configured for MCP registration")
        await self._self_mutation.add_mcp_server(
            McpServerId(server_id), command, args, env
        )
