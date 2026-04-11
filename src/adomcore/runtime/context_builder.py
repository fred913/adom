"""BuiltContext — assembled input for a single agent turn."""

import json
from typing import Any

from pydantic.dataclasses import dataclass

from adomcore.domain.memory import CompactSnapshot
from adomcore.domain.models import ModelSpec
from adomcore.domain.skills import SkillSpec


@dataclass
class BuiltContext:
    system_prompt: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    model_spec: ModelSpec
    recent_event_count: int
    estimated_tokens: int


class ContextBuilder:
    def __init__(
        self,
        thread_store: object,
        compact_store: object,
        skill_service: object,
        capability_registry: object,
        model_service: object,
    ) -> None:
        self._threads = thread_store
        self._compact = compact_store
        self._skills = skill_service
        self._caps = capability_registry
        self._models = model_service

    def build(
        self,
        thread_id: object,
        active_model_id: str,
        recent_window: int = 24,
    ) -> BuiltContext:
        from adomcore.domain.ids import ThreadId
        from adomcore.services.capability_registry import CapabilityRegistry
        from adomcore.services.model_service import ModelService
        from adomcore.services.skill_service import SkillService
        from adomcore.storage.stores.compact_store import CompactStore
        from adomcore.storage.stores.thread_store import ThreadStore

        assert isinstance(self._threads, ThreadStore)
        assert isinstance(self._compact, CompactStore)
        assert isinstance(self._skills, SkillService)
        assert isinstance(self._caps, CapabilityRegistry)
        assert isinstance(self._models, ModelService)
        assert isinstance(thread_id, str)

        tid = ThreadId(thread_id)
        model_spec = self._models.get_active(active_model_id)
        compact: CompactSnapshot | None = self._compact.load(tid)
        events = self._threads.read_events(tid, tail=recent_window)
        skills: list[SkillSpec] = self._skills.list_enabled()

        system_parts = ["You are a helpful AI agent."]
        if compact:
            system_parts.append(f"\n## Long-term memory\n{compact.summary}")
            if compact.facts:
                system_parts.append(
                    "Facts: " + "; ".join(f.content for f in compact.facts)
                )
            if compact.preferences:
                system_parts.append(
                    "Preferences: " + "; ".join(p.content for p in compact.preferences)
                )
        if skills:
            system_parts.append(
                "\n## Skills\n" + "\n".join(f"- {s.name}: {s.content}" for s in skills)
            )

        messages: list[dict[str, Any]] = []
        for ev in events:
            et = ev.get("event_type")
            payload = ev.get("payload", {})
            if et == "user_message":
                messages.append({"role": "user", "content": payload.get("text", "")})
            elif et == "assistant_message":
                messages.append(
                    {"role": "assistant", "content": payload.get("text", "")}
                )
            elif et == "assistant_tool_call":
                messages.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": payload.get("call_id", ""),
                                "type": "function",
                                "function": {
                                    "name": payload.get("tool_name", ""),
                                    "arguments": json.dumps(
                                        payload.get("arguments", {}),
                                        ensure_ascii=False,
                                    ),
                                },
                            }
                        ],
                    }
                )
            elif et == "tool_result":
                messages.append(
                    {
                        "role": "tool",
                        "content": str(payload.get("result", "")),
                        "tool_call_id": payload.get("call_id", ""),
                    }
                )

        tools = [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
            }
            for spec in self._caps.list_enabled()
        ]

        return BuiltContext(
            system_prompt="\n".join(system_parts),
            messages=messages,
            tools=tools,
            model_spec=model_spec,
            recent_event_count=len(events),
            estimated_tokens=sum(len(str(m)) // 4 for m in messages),
        )
