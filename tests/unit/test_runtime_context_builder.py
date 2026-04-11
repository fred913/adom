from datetime import UTC, datetime
from pathlib import Path

from adomcore.domain.events import EventEnvelope
from adomcore.domain.ids import ThreadId
from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.runtime.context_builder import ContextBuilder
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.model_service import ModelService
from adomcore.services.skill_service import SkillService
from adomcore.storage.json5_store import Json5Store
from adomcore.storage.jsonl_store import JsonlStore
from adomcore.storage.path_resolver import PathResolver
from adomcore.storage.stores.compact_store import CompactStore
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
