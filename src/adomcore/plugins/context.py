"""PluginContext — restricted interface exposed to plugins."""

from collections.abc import Callable
from typing import Any

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import McpServerId, SkillId
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.model_service import ModelService
from adomcore.services.plugin_model_gateway import PluginModelGateway, PluginModelHandle


class PluginContext:
    def __init__(
        self,
        registry: CapabilityRegistry,
        self_mutation_service: object | None = None,
        model_gateway: PluginModelGateway | None = None,
    ) -> None:
        self._registry = registry
        self._self_mutation = self_mutation_service
        self._model_gateway = model_gateway

    @property
    def model_service(self) -> ModelService:
        if self._model_gateway is None:
            raise RuntimeError("PluginContext is not configured for model access")
        return self._model_gateway.model_service

    def get_model(self, model_id: str | None = None) -> PluginModelHandle:
        if self._model_gateway is None:
            raise RuntimeError("PluginContext is not configured for model access")
        return self._model_gateway.get_model(model_id)

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
