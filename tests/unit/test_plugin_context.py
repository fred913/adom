from pathlib import Path
from typing import cast

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
from adomcore.services.tool_executor import ToolExecutor
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
async def test_plugin_manager_collects_declared_functions_and_skills(
    tmp_path: Path,
) -> None:
    plugin_file = tmp_path / "plugin.py"
    plugin_file.write_text(
        """
from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import SkillId
from adomcore.domain.skills import SkillSpec
from adomcore.plugins.base import BasePlugin

class DeclPlugin(BasePlugin):
    plugin_id = 'decl_plugin'
    plugin_name = 'Decl Plugin'

    def functions(self):
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name='demo_tool',
                    description='Demo tool',
                    input_schema={'type': 'object', 'properties': {}},
                    source_plugin=self.id,
                ),
                handler=lambda: {'status': 'ok'},
            )
        ]

    def skills(self):
        return [
            SkillSpec(
                id=SkillId('async_skill'),
                name='Async skill',
                content='Registered declaratively',
            )
        ]

    def system_prompt(self):
        return 'Plugin prompt text.'

plugin = DeclPlugin
""".strip(),
        encoding="utf-8",
    )

    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    registry = CapabilityRegistry()
    store = PluginStore(resolver, json5)
    manager = PluginManager(store, PluginLoader(), registry)

    desc = PluginDescriptor(
        id=PluginId("decl_plugin"),
        name="Decl Plugin",
        version="0.1.0",
        description="",
        manifest_path=str(tmp_path / "plugin.yaml"),
    )

    await store.save_registry([desc])
    await manager.load_all()

    assert registry.get_spec("demo_tool") is not None
    plugin = next(
        plugin for plugin in manager.list_all() if plugin.id == PluginId("decl_plugin")
    )
    assert plugin.name == "Decl Plugin"
    assert plugin.description == ""
    assert [skill.id for skill in manager.list_enabled_skills()] == [
        SkillId("async_skill")
    ]
    assert manager.system_prompt_parts() == ["Plugin prompt text."]


@pytest.mark.asyncio
async def test_plugin_manager_sorts_system_prompts_by_priority(tmp_path: Path) -> None:
    high_plugin_file = tmp_path / "plugin.py"
    high_plugin_file.write_text(
        """
from adomcore.plugins.base import BasePlugin

class PriorityPlugin(BasePlugin):
    plugin_id = 'priority_plugin'
    plugin_name = 'Priority Plugin'

    def system_prompt(self):
        return ('High priority prompt.', 100)

plugin = PriorityPlugin
""".strip(),
        encoding="utf-8",
    )

    low_plugin_dir = tmp_path / "low"
    low_plugin_dir.mkdir()
    low_plugin_file = low_plugin_dir / "plugin.py"
    low_plugin_file.write_text(
        """
from adomcore.plugins.base import BasePlugin

class LowPriorityPlugin(BasePlugin):
    plugin_id = 'low_priority_plugin'
    plugin_name = 'Low Priority Plugin'

    def system_prompt(self):
        return ('Low priority prompt.', 1)

plugin = LowPriorityPlugin
""".strip(),
        encoding="utf-8",
    )

    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    registry = CapabilityRegistry()
    store = PluginStore(resolver, json5)
    manager = PluginManager(store, PluginLoader(), registry, builtin_descriptors=[])

    await store.save_registry(
        [
            PluginDescriptor(
                id=PluginId("priority_plugin"),
                name="Priority Plugin",
                version="0.1.0",
                description="",
                manifest_path=str(tmp_path / "plugin.yaml"),
            ),
            PluginDescriptor(
                id=PluginId("low_priority_plugin"),
                name="Low Priority Plugin",
                version="0.1.0",
                description="",
                manifest_path=str(low_plugin_dir / "plugin.yaml"),
            ),
        ]
    )

    await manager.load_all()

    assert manager.system_prompt_parts() == [
        "High priority prompt.",
        "Low priority prompt.",
    ]


@pytest.mark.asyncio
async def test_plugin_functions_are_computed_dynamically(tmp_path: Path) -> None:
    plugin_file = tmp_path / "plugin.py"
    plugin_file.write_text(
        """
from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.plugins.base import BasePlugin

class DynamicPlugin(BasePlugin):
    plugin_id = 'dynamic_plugin'
    plugin_name = 'Dynamic Plugin'

    def __init__(self):
        super().__init__()
        self.expose_dynamic = False

    def functions(self):
        if not self.expose_dynamic:
            return []
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name='dynamic_tool',
                    description='Dynamic tool',
                    input_schema={'type': 'object', 'properties': {}},
                    source_plugin=self.id,
                ),
                handler=lambda: {'status': 'dynamic'},
            )
        ]

plugin = DynamicPlugin
""".strip(),
        encoding="utf-8",
    )

    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    registry = CapabilityRegistry()
    store = PluginStore(resolver, json5)
    manager = PluginManager(store, PluginLoader(), registry)
    executor = ToolExecutor(registry)

    desc = PluginDescriptor(
        id=PluginId("dynamic_plugin"),
        name="Dynamic Plugin",
        version="0.1.0",
        description="",
        manifest_path=str(tmp_path / "plugin.yaml"),
    )

    await store.save_registry([desc])
    await manager.load_all()

    assert registry.get_spec("dynamic_tool") is None

    plugin = next(
        plugin
        for plugin in manager.list_all()
        if plugin.id == PluginId("dynamic_plugin")
    )
    dynamic_plugin = cast(object, plugin)
    setattr(dynamic_plugin, "expose_dynamic", True)

    spec = registry.get_spec("dynamic_tool")

    assert spec is not None
    assert spec.source_plugin == PluginId("dynamic_plugin")
    assert await executor.execute("dynamic_tool", {}) == {"status": "dynamic"}
