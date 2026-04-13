"""AppContainer — single dependency container for the whole process."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import field
from typing import Any

from pydantic.dataclasses import dataclass

from adomcore.app.paths import AppPaths, PathFactory
from adomcore.app.settings import AppSettings
from adomcore.domain.actions import AgentDecision, RespondAction
from adomcore.domain.models import (
    ModelProviderKind,
    ModelSpec,
    ModelSpec_OpenAICompatible,
)
from adomcore.domain.policies import TokenBudgetPolicy
from adomcore.domain.streaming import EngineDecisionEvent, EngineEvent
from adomcore.integrations.llm.engine_protocol import AgentEngine
from adomcore.plugins.context import PluginContext
from adomcore.runtime.action_router import ActionRouter
from adomcore.runtime.agent_runtime import AgentRuntime
from adomcore.runtime.compact_manager import CompactManager
from adomcore.runtime.context_builder import ContextBuilder
from adomcore.services.agent_service import AgentService
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.compact_service import CompactService
from adomcore.services.conversation_service import ConversationService
from adomcore.services.cron_dispatch_service import CronDispatchService
from adomcore.services.mcp_service import McpService
from adomcore.services.mcp_session_manager import McpSessionManager
from adomcore.services.model_service import ModelService
from adomcore.services.plugin_loader import PluginLoader
from adomcore.services.plugin_manager import PluginManager
from adomcore.services.plugin_model_gateway import PluginModelGateway
from adomcore.services.scheduler_service import SchedulerService
from adomcore.services.self_mutation_service import SelfMutationService
from adomcore.services.skill_service import SkillService
from adomcore.services.tool_executor import ToolExecutor
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.jsonl_store import JsonlStore
from adomcore.storage.stores.agent_state_store import AgentStateStore
from adomcore.storage.stores.compact_store import CompactStore
from adomcore.storage.stores.cron_store import CronStore
from adomcore.storage.stores.mcp_store import McpStore
from adomcore.storage.stores.plugin_store import PluginStore
from adomcore.storage.stores.runtime_store import RuntimeStore
from adomcore.storage.stores.skill_store import SkillStore
from adomcore.storage.stores.thread_store import ThreadStore


class _DefaultAgentEngine:
    async def decide(self, context: dict[str, Any]) -> AgentDecision:
        return AgentDecision(actions=[RespondAction(text="")])

    async def stream_decide(
        self, context: dict[str, Any]
    ) -> AsyncIterator[EngineEvent]:
        yield EngineDecisionEvent(kind="decision", decision=await self.decide(context))

    async def summarise(self, prompt: str) -> dict[str, Any]:
        return {
            "summary": "",
            "facts": [],
            "preferences": [],
            "tasks": [],
            "important_decisions": [],
            "recent_capability_changes": [],
        }


def _default_settings() -> AppSettings:
    return AppSettings()


def _default_paths() -> AppPaths:
    settings = _default_settings()
    return PathFactory.from_settings(settings.storage.root_dir)


def _default_json5() -> Json5Store:
    return Json5Store()


def _default_jsonl() -> JsonlStore:
    return JsonlStore()


def _default_agent_state_store() -> AgentStateStore:
    paths = _default_paths()
    return AgentStateStore(paths.resolver, _default_json5())


def _default_thread_store() -> ThreadStore:
    paths = _default_paths()
    return ThreadStore(paths.resolver, _default_json5(), _default_jsonl())


def _default_skill_store() -> SkillStore:
    paths = _default_paths()
    return SkillStore(paths.resolver, _default_json5())


def _default_plugin_store() -> PluginStore:
    paths = _default_paths()
    return PluginStore(paths.resolver, _default_json5())


def _default_mcp_store() -> McpStore:
    paths = _default_paths()
    return McpStore(paths.resolver, _default_json5())


def _default_cron_store() -> CronStore:
    paths = _default_paths()
    return CronStore(paths.resolver, _default_json5(), _default_jsonl())


def _default_compact_store() -> CompactStore:
    paths = _default_paths()
    return CompactStore(paths.resolver, _default_json5())


def _default_runtime_store() -> RuntimeStore:
    paths = _default_paths()
    return RuntimeStore(paths.resolver, _default_json5())


def _default_agent_service() -> AgentService:
    return AgentService(_default_agent_state_store())


def _default_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry()


def _default_skill_service() -> SkillService:
    return SkillService(_default_skill_store())


def _default_mcp_service() -> McpService:
    return McpService(_default_mcp_store())


def _default_mcp_session_manager() -> McpSessionManager:
    return McpSessionManager(_default_mcp_store())


def _default_tool_executor() -> ToolExecutor:
    return ToolExecutor(_default_capability_registry())


def _default_plugin_loader() -> PluginLoader:
    settings = _default_settings()
    return PluginLoader(settings.plugins.config)


def _default_model_spec() -> ModelSpec:
    return ModelSpec_OpenAICompatible(
        id="main",
        provider=ModelProviderKind.OPENAI_COMPATIBLE,
        model="default",
        context_window=32000,
    )


def _default_model_service() -> ModelService:
    spec = _default_model_spec()
    return ModelService([spec], spec.id)


def _default_plugin_model_gateway() -> PluginModelGateway:
    return PluginModelGateway(_default_model_service())


def _default_engine() -> AgentEngine:
    return _DefaultAgentEngine()


def _default_compact_service() -> CompactService:
    return CompactService(
        _default_thread_store(), _default_compact_store(), _default_engine()
    )


def _default_self_mutation_service() -> SelfMutationService:
    return SelfMutationService(
        _default_agent_service(),
        _default_skill_service(),
        _default_mcp_service(),
    )


def _default_scheduler_service() -> SchedulerService:
    return SchedulerService(_default_cron_store())


def _default_context_builder() -> ContextBuilder:
    return ContextBuilder(
        _default_thread_store(),
        _default_compact_store(),
        _default_skill_service(),
        _default_capability_registry(),
        _default_plugin_manager(),
        _default_model_service(),
    )


def _default_action_router() -> ActionRouter:
    return ActionRouter(
        _default_tool_executor(),
        _default_mcp_session_manager(),
        _default_self_mutation_service(),
        _default_scheduler_service(),
    )


def _default_compact_manager() -> CompactManager:
    return CompactManager(
        _default_thread_store(),
        _default_compact_service(),
        TokenBudgetPolicy(),
    )


def _default_agent_runtime() -> AgentRuntime:
    settings = _default_settings()
    return AgentRuntime(
        _default_agent_service(),
        _default_thread_store(),
        _default_context_builder(),
        _default_action_router(),
        _default_compact_manager(),
        _default_engine(),
        max_loop_steps=settings.runtime.max_loop_steps,
    )


def _default_conversation_service() -> ConversationService:
    return ConversationService(_default_agent_runtime())


def _default_cron_dispatch_service() -> CronDispatchService:
    return CronDispatchService(_default_scheduler_service(), _default_agent_runtime())


def _default_plugin_manager() -> PluginManager:
    registry = _default_capability_registry()
    plugin_context = PluginContext(
        registry,
        _default_self_mutation_service(),
        _default_plugin_model_gateway(),
    )
    return PluginManager(
        _default_plugin_store(),
        _default_plugin_loader(),
        registry,
        plugin_context,
    )


@dataclass(config={"arbitrary_types_allowed": True})
class AppContainer:
    settings: AppSettings = field(default_factory=_default_settings)
    paths: AppPaths = field(default_factory=_default_paths)
    # stores
    agent_state_store: AgentStateStore = field(
        default_factory=_default_agent_state_store
    )
    thread_store: ThreadStore = field(default_factory=_default_thread_store)
    skill_store: SkillStore = field(default_factory=_default_skill_store)
    plugin_store: PluginStore = field(default_factory=_default_plugin_store)
    mcp_store: McpStore = field(default_factory=_default_mcp_store)
    cron_store: CronStore = field(default_factory=_default_cron_store)
    compact_store: CompactStore = field(default_factory=_default_compact_store)
    runtime_store: RuntimeStore = field(default_factory=_default_runtime_store)
    # services
    agent_service: AgentService = field(default_factory=_default_agent_service)
    model_service: ModelService = field(default_factory=_default_model_service)
    capability_registry: CapabilityRegistry = field(
        default_factory=_default_capability_registry
    )
    skill_service: SkillService = field(default_factory=_default_skill_service)
    mcp_service: McpService = field(default_factory=_default_mcp_service)
    mcp_session_manager: McpSessionManager = field(
        default_factory=_default_mcp_session_manager
    )
    tool_executor: ToolExecutor = field(default_factory=_default_tool_executor)
    plugin_loader: PluginLoader = field(default_factory=_default_plugin_loader)
    plugin_manager: PluginManager = field(default_factory=_default_plugin_manager)
    plugin_model_gateway: PluginModelGateway = field(
        default_factory=_default_plugin_model_gateway
    )
    scheduler_service: SchedulerService = field(
        default_factory=_default_scheduler_service
    )
    compact_service: CompactService = field(default_factory=_default_compact_service)
    self_mutation_service: SelfMutationService = field(
        default_factory=_default_self_mutation_service
    )
    conversation_service: ConversationService = field(
        default_factory=_default_conversation_service
    )
    cron_dispatch_service: CronDispatchService = field(
        default_factory=_default_cron_dispatch_service
    )
    # runtime
    engine: AgentEngine = field(default_factory=_default_engine)
    context_builder: ContextBuilder = field(default_factory=_default_context_builder)
    action_router: ActionRouter = field(default_factory=_default_action_router)
    compact_manager: CompactManager = field(default_factory=_default_compact_manager)
    agent_runtime: AgentRuntime = field(default_factory=_default_agent_runtime)
