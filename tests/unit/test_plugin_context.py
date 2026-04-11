from pathlib import Path

import pytest

from adomcore.domain.ids import McpServerId, PluginId, SkillId
from adomcore.domain.plugins import PluginDescriptor
from adomcore.plugins.context import PluginContext
from adomcore.services.agent_service import AgentService
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.mcp_service import McpService
from adomcore.services.plugin_loader import PluginLoader
from adomcore.services.plugin_manager import PluginManager
from adomcore.services.self_mutation_service import SelfMutationService
from adomcore.services.skill_service import SkillService
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.path_resolver import PathResolver
from adomcore.storage.stores.agent_state_store import AgentStateStore
from adomcore.storage.stores.mcp_store import McpStore
from adomcore.storage.stores.plugin_store import PluginStore
from adomcore.storage.stores.skill_store import SkillStore


@pytest.mark.asyncio
async def test_plugin_context_registers_skill_and_mcp(tmp_path: Path) -> None:
    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    agent_service = AgentService(AgentStateStore(resolver, json5))
    skill_service = SkillService(SkillStore(resolver, json5))
    mcp_service = McpService(McpStore(resolver, json5))
    ctx = PluginContext(
        CapabilityRegistry(),
        SelfMutationService(agent_service, skill_service, mcp_service),
    )

    await ctx.register_skill("demo_skill", "Demo skill", "Use tools.")
    await ctx.register_mcp_server("demo_mcp", "python", ["-m", "demo"], {"A": "1"})

    assert skill_service.get(SkillId("demo_skill")) is not None
    assert mcp_service.get(McpServerId("demo_mcp")) is not None


@pytest.mark.asyncio
async def test_plugin_manager_supports_async_setup(tmp_path: Path) -> None:
    plugin_file = tmp_path / "async_plugin.py"
    plugin_file.write_text(
        """
class AsyncPlugin:
    async def setup(self, ctx):
        await ctx.register_skill('async_skill', 'Async skill', 'Registered asynchronously')

plugin = AsyncPlugin
""".strip(),
        encoding="utf-8",
    )

    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    registry = CapabilityRegistry()
    agent_service = AgentService(AgentStateStore(resolver, json5))
    skill_service = SkillService(SkillStore(resolver, json5))
    mcp_service = McpService(McpStore(resolver, json5))
    ctx = PluginContext(
        registry,
        SelfMutationService(agent_service, skill_service, mcp_service),
    )
    store = PluginStore(resolver, json5)
    manager = PluginManager(store, PluginLoader(), registry, ctx)

    desc = PluginDescriptor(
        id=PluginId("async_plugin"),
        name="Async Plugin",
        version="0.1.0",
        description="",
        entry_point="async_plugin:plugin",
        builtin=False,
        manifest_path=str(tmp_path / "plugin.yaml"),
    )

    await store.save_registry([desc])
    await manager.load_all()

    assert skill_service.get(SkillId("async_skill")) is not None
