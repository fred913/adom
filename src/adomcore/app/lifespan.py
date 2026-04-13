"""AppLifespan — startup and shutdown orchestration."""

from loguru import logger

from adomcore.app.container import AppContainer
from adomcore.app.logging import setup_logging
from adomcore.app.paths import PathFactory
from adomcore.app.settings import AppSettings
from adomcore.plugins.context import PluginContext


async def build_container(settings: AppSettings) -> AppContainer:
    c = AppContainer()
    c.settings = settings

    # paths
    c.paths = PathFactory.from_settings(settings.storage.root_dir)
    setup_logging(c.paths.logs_dir)

    # storage primitives
    from adomcore.storage.json5_store import Json5Store
    from adomcore.storage.jsonl_store import JsonlStore

    json5 = Json5Store()
    jsonl = JsonlStore()

    # stores
    from adomcore.storage.stores.agent_state_store import AgentStateStore
    from adomcore.storage.stores.compact_store import CompactStore
    from adomcore.storage.stores.cron_store import CronStore
    from adomcore.storage.stores.mcp_store import McpStore
    from adomcore.storage.stores.plugin_store import PluginStore
    from adomcore.storage.stores.runtime_store import RuntimeStore
    from adomcore.storage.stores.skill_store import SkillStore
    from adomcore.storage.stores.thread_store import ThreadStore

    r = c.paths.resolver
    c.agent_state_store = AgentStateStore(r, json5)
    c.thread_store = ThreadStore(r, json5, jsonl)
    c.skill_store = SkillStore(r, json5)
    c.plugin_store = PluginStore(r, json5)
    c.mcp_store = McpStore(r, json5)
    c.cron_store = CronStore(r, json5, jsonl)
    c.compact_store = CompactStore(r, json5)
    c.runtime_store = RuntimeStore(r, json5)

    # services
    from adomcore.domain.models import (
        ModelProviderKind,
        ModelSpec,
        TokenEstimateProviderKind,
    )
    from adomcore.services.agent_service import AgentService
    from adomcore.services.capability_registry import CapabilityRegistry
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

    c.agent_service = AgentService(c.agent_state_store)
    c.capability_registry = CapabilityRegistry()
    c.skill_service = SkillService(c.skill_store)
    c.mcp_service = McpService(c.mcp_store)
    c.mcp_session_manager = McpSessionManager(c.mcp_store)
    c.tool_executor = ToolExecutor(c.capability_registry)

    # model service
    model_specs = [
        ModelSpec(
            id=m["id"],
            provider=ModelProviderKind(m["provider"]),
            model=m["model"],
            context_window=m.get("context_window", 32000),
            supports_tools=m.get("supports_tools", True),
            supports_structured_output=m.get("supports_structured_output", True),
            supports_streaming=m.get("supports_streaming", True),
            enabled=m.get("enabled", True),
            api_base=m.get("api_base"),
            api_key=m.get("api_key"),
            extra_config=m.get("extra_config") or {},
            token_estimate_provider=TokenEstimateProviderKind(
                m.get("token_estimate_provider", "heuristic")
            ),
            token_estimate_config=m.get("token_estimate_config") or {},
        )
        for m in settings.models
    ]
    c.model_service = ModelService(model_specs, settings.default_model_id)
    c.plugin_model_gateway = PluginModelGateway(c.model_service)

    # engine
    state = c.agent_service.load()
    active_spec = c.model_service.get_active(state.active_model_id)
    from adomcore.integrations.llm.atomic_agents_engine import AtomicAgentsEngine

    c.engine = AtomicAgentsEngine(active_spec)

    # compact service
    from adomcore.services.compact_service import CompactService

    c.compact_service = CompactService(c.thread_store, c.compact_store, c.engine)

    # runtime
    from adomcore.domain.policies import TokenBudgetPolicy
    from adomcore.runtime.action_router import ActionRouter
    from adomcore.runtime.agent_runtime import AgentRuntime
    from adomcore.runtime.compact_manager import CompactManager
    from adomcore.runtime.context_builder import ContextBuilder

    c.self_mutation_service = SelfMutationService(
        c.agent_service, c.skill_service, c.mcp_service
    )
    c.scheduler_service = SchedulerService(c.cron_store)
    c.plugin_loader = PluginLoader(settings.plugins.config)
    plugin_context = PluginContext(
        c.capability_registry,
        c.self_mutation_service,
        c.plugin_model_gateway,
    )
    c.plugin_manager = PluginManager(
        c.plugin_store,
        c.plugin_loader,
        c.capability_registry,
        plugin_context,
    )
    c.context_builder = ContextBuilder(
        c.thread_store,
        c.compact_store,
        c.skill_service,
        c.capability_registry,
        c.plugin_manager,
        c.model_service,
    )
    c.action_router = ActionRouter(
        c.tool_executor,
        c.mcp_session_manager,
        c.self_mutation_service,
        c.scheduler_service,
    )
    policy = TokenBudgetPolicy(
        soft_ratio=settings.runtime.compact_soft_ratio,
        hard_ratio=settings.runtime.compact_hard_ratio,
        recent_messages_window=settings.runtime.recent_messages_window,
    )
    c.compact_manager = CompactManager(c.thread_store, c.compact_service, policy)
    c.agent_runtime = AgentRuntime(
        c.agent_service,
        c.thread_store,
        c.context_builder,
        c.action_router,
        c.compact_manager,
        c.engine,
        max_loop_steps=settings.runtime.max_loop_steps,
    )

    # conversation service
    from adomcore.services.conversation_service import ConversationService

    c.conversation_service = ConversationService(c.agent_runtime)

    # cron dispatch
    from adomcore.services.cron_dispatch_service import CronDispatchService

    c.cron_dispatch_service = CronDispatchService(c.scheduler_service, c.agent_runtime)
    c.scheduler_service.set_dispatch_callback(c.cron_dispatch_service.dispatch)

    # scheduler backend
    from adomcore.integrations.scheduler.apscheduler_backend import APSchedulerBackend

    backend = APSchedulerBackend()
    c.scheduler_service.set_backend(backend)

    return c


async def startup(c: AppContainer) -> None:
    import datetime
    import os

    from adomcore.app.settings import AppSettings

    assert isinstance(c.settings, AppSettings)

    # ensure default thread dir
    from adomcore.domain.ids import ThreadId
    from adomcore.storage.stores.thread_store import ThreadStore

    assert isinstance(c.thread_store, ThreadStore)
    c.thread_store.ensure_thread_dir(ThreadId(c.settings.default_thread_id))

    # write boot record
    from adomcore.storage.stores.runtime_store import RuntimeStore

    assert isinstance(c.runtime_store, RuntimeStore)
    await c.runtime_store.write_boot(os.getpid(), datetime.datetime.now(datetime.UTC))

    # start scheduler
    from adomcore.services.scheduler_service import SchedulerService

    assert isinstance(c.scheduler_service, SchedulerService)
    await c.scheduler_service.start()

    logger.info("adomcore started")


async def shutdown(c: AppContainer) -> None:
    from adomcore.services.mcp_session_manager import McpSessionManager
    from adomcore.services.scheduler_service import SchedulerService

    assert isinstance(c.scheduler_service, SchedulerService)
    assert isinstance(c.mcp_session_manager, McpSessionManager)
    await c.scheduler_service.stop()
    await c.mcp_session_manager.disconnect_all()
    logger.info("adomcore stopped")
