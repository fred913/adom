from datetime import UTC, datetime
from pathlib import Path

from adomcore.domain.events import EventEnvelope
from adomcore.domain.ids import PluginId, ThreadId
from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.domain.plugins import PluginDescriptor
from adomcore.runtime.context_builder import ContextBuilder
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.model_service import ModelService
from adomcore.services.plugin_loader import PluginLoader
from adomcore.services.plugin_manager import PluginManager
from adomcore.services.skill_service import SkillService
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.jsonl_store import JsonlStore
from adomcore.storage.path_resolver import PathResolver
from adomcore.storage.stores.compact_store import CompactStore
from adomcore.storage.stores.plugin_store import PluginStore
from adomcore.storage.stores.skill_store import SkillStore
from adomcore.storage.stores.thread_store import ThreadStore


async def test_context_builder_reconstructs_openai_tool_call_history(
    tmp_path: Path,
) -> None:
    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    jsonl = JsonlStore()
    thread_store = ThreadStore(resolver, json5, jsonl)
    compact_store = CompactStore(resolver, json5)
    skill_service = SkillService(SkillStore(resolver, json5))
    capability_registry = CapabilityRegistry()
    plugin_store = PluginStore(resolver, json5)
    plugin_manager = PluginManager(plugin_store, PluginLoader(), capability_registry)
    model_service = ModelService(
        [
            ModelSpec(
                id="main",
                provider=ModelProviderKind.OPENAI_COMPATIBLE,
                model="gpt-4o-mini",
                context_window=32000,
            )
        ],
        default_model_id="main",
    )
    builder = ContextBuilder(
        thread_store,
        compact_store,
        skill_service,
        capability_registry,
        plugin_manager,
        model_service,
    )

    tid = ThreadId("main")
    thread_store.ensure_thread_dir(tid)
    await thread_store.append_event(
        EventEnvelope(
            event_id="evt_user",
            event_type="user_message",
            ts=datetime(2026, 4, 11, 14, 0, 0, tzinfo=UTC),
            thread_id=tid,
            payload={"text": "What time is it?"},
        )
    )
    await thread_store.append_event(
        EventEnvelope(
            event_id="evt_tool_call",
            event_type="assistant_tool_call",
            ts=datetime(2026, 4, 11, 14, 0, 1, tzinfo=UTC),
            thread_id=tid,
            payload={
                "call_id": "call_123",
                "tool_name": "format_time",
                "arguments": {},
            },
        )
    )
    await thread_store.append_event(
        EventEnvelope(
            event_id="evt_tool_result",
            event_type="tool_result",
            ts=datetime(2026, 4, 11, 14, 0, 2, tzinfo=UTC),
            thread_id=tid,
            payload={"call_id": "call_123", "result": '{"time":"now"}'},
        )
    )

    context = builder.build(thread_id="main", active_model_id="main")

    assert context.messages[1] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "format_time", "arguments": "{}"},
            }
        ],
    }
    assert context.messages[2] == {
        "role": "tool",
        "content": '{"time":"now"}',
        "tool_call_id": "call_123",
    }


async def test_context_builder_includes_plugin_skills_and_system_prompt(
    tmp_path: Path,
) -> None:
    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    jsonl = JsonlStore()
    thread_store = ThreadStore(resolver, json5, jsonl)
    compact_store = CompactStore(resolver, json5)
    skill_service = SkillService(SkillStore(resolver, json5))
    capability_registry = CapabilityRegistry()
    plugin_store = PluginStore(resolver, json5)
    plugin_manager = PluginManager(plugin_store, PluginLoader(), capability_registry)
    model_service = ModelService(
        [
            ModelSpec(
                id="main",
                provider=ModelProviderKind.OPENAI_COMPATIBLE,
                model="gpt-4o-mini",
                context_window=32000,
            )
        ],
        default_model_id="main",
    )
    builder = ContextBuilder(
        thread_store,
        compact_store,
        skill_service,
        capability_registry,
        plugin_manager,
        model_service,
    )

    plugin_file = tmp_path / "plugin.py"
    plugin_file.write_text(
        """
from adomcore.domain.ids import SkillId
from adomcore.domain.skills import SkillSpec
from adomcore.plugins.base import BasePlugin

class ContextPlugin(BasePlugin):
    plugin_id = 'context_plugin'
    plugin_name = 'Context Plugin'

    def skills(self):
        return [SkillSpec(id=SkillId('plugin_skill'), name='Plugin Skill', content='From plugin')]

    def system_prompt(self):
        return 'Plugin system prompt.'

plugin = ContextPlugin
""".strip(),
        encoding="utf-8",
    )
    desc = PluginDescriptor(
        id=PluginId("context_plugin"),
        name="Context Plugin",
        version="0.1.0",
        description="",
        manifest_path=str(tmp_path / "plugin.yaml"),
    )
    await plugin_store.save_registry([desc])
    await plugin_manager.load_all()

    context = builder.build(thread_id="main", active_model_id="main")

    assert "Plugin system prompt." in context.system_prompt
    assert "- Plugin Skill: From plugin" in context.system_prompt
    plugin = next(
        plugin
        for plugin in plugin_manager.list_all()
        if plugin.id == PluginId("context_plugin")
    )
    assert plugin.name == "Context Plugin"


async def test_context_builder_orders_plugin_system_prompts_by_priority(
    tmp_path: Path,
) -> None:
    resolver = PathResolver(tmp_path)
    json5 = Json5Store()
    jsonl = JsonlStore()
    thread_store = ThreadStore(resolver, json5, jsonl)
    compact_store = CompactStore(resolver, json5)
    skill_service = SkillService(SkillStore(resolver, json5))
    capability_registry = CapabilityRegistry()
    plugin_store = PluginStore(resolver, json5)
    plugin_manager = PluginManager(
        plugin_store, PluginLoader(), capability_registry, builtin_descriptors=[]
    )
    model_service = ModelService(
        [
            ModelSpec(
                id="main",
                provider=ModelProviderKind.OPENAI_COMPATIBLE,
                model="gpt-4o-mini",
                context_window=32000,
            )
        ],
        default_model_id="main",
    )
    builder = ContextBuilder(
        thread_store,
        compact_store,
        skill_service,
        capability_registry,
        plugin_manager,
        model_service,
    )

    high_dir = tmp_path / "high"
    high_dir.mkdir()
    (high_dir / "plugin.py").write_text(
        """
from adomcore.plugins.base import BasePlugin

class HighPromptPlugin(BasePlugin):
    plugin_id = 'high_prompt'
    plugin_name = 'High Prompt'

    def system_prompt(self):
        return ('High prompt.', 100)

plugin = HighPromptPlugin
""".strip(),
        encoding="utf-8",
    )

    low_dir = tmp_path / "low"
    low_dir.mkdir()
    (low_dir / "plugin.py").write_text(
        """
from adomcore.plugins.base import BasePlugin

class LowPromptPlugin(BasePlugin):
    plugin_id = 'low_prompt'
    plugin_name = 'Low Prompt'

    def system_prompt(self):
        return ('Low prompt.', -1)

plugin = LowPromptPlugin
""".strip(),
        encoding="utf-8",
    )

    await plugin_store.save_registry(
        [
            PluginDescriptor(
                id=PluginId("low_prompt"),
                name="Low Prompt",
                version="0.1.0",
                description="",
                manifest_path=str(low_dir / "plugin.yaml"),
            ),
            PluginDescriptor(
                id=PluginId("high_prompt"),
                name="High Prompt",
                version="0.1.0",
                description="",
                manifest_path=str(high_dir / "plugin.yaml"),
            ),
        ]
    )
    await plugin_manager.load_all()

    context = builder.build(thread_id="main", active_model_id="main")

    assert context.system_prompt.index("High prompt.") < context.system_prompt.index(
        "Low prompt."
    )
