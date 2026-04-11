"""Compact service — summarise thread history into CompactSnapshot."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from adomcore.domain.ids import ThreadId
from adomcore.domain.memory import (
    CompactSnapshot,
    MemoryFact,
    MemoryPreference,
    MemoryTask,
)
from adomcore.storage.stores.compact_store import CompactStore
from adomcore.storage.stores.thread_store import ThreadStore

if TYPE_CHECKING:
    from adomcore.integrations.llm.engine_protocol import AgentEngine


class CompactService:
    def __init__(
        self,
        thread_store: ThreadStore,
        compact_store: CompactStore,
        engine: AgentEngine,
    ) -> None:
        self._threads = thread_store
        self._compact = compact_store
        self._engine = engine

    async def compact(self, tid: ThreadId) -> CompactSnapshot:
        events = self._threads.read_events(tid)
        existing = self._compact.load(tid)

        prompt = self._build_compact_prompt(events, existing)
        raw: dict[str, Any] = await self._engine.summarise(prompt)

        snapshot = CompactSnapshot(
            thread_id=tid,
            summary=raw.get("summary", ""),
            facts=[MemoryFact(content=f) for f in raw.get("facts", [])],
            preferences=[
                MemoryPreference(content=p) for p in raw.get("preferences", [])
            ],
            tasks=[
                MemoryTask(content=t["content"], status=t.get("status", "open"))
                for t in raw.get("tasks", [])
            ],
            important_decisions=raw.get("important_decisions", []),
            recent_capability_changes=raw.get("recent_capability_changes", []),
            compacted_at=datetime.now(UTC),
            covers_up_to_event_id=(events[-1].get("event_id") if events else None),
        )
        await self._compact.save(snapshot)
        logger.info("Compacted thread {} ({} events)", tid, len(events))
        return snapshot

    @staticmethod
    def _build_compact_prompt(
        events: list[dict[str, Any]],
        existing: CompactSnapshot | None,
    ) -> str:
        lines = [
            "Summarise the following conversation into a structured memory snapshot.",
            "Return JSON with keys: summary, facts (list[str]), preferences (list[str]),",
            "tasks (list[{content, status}]), important_decisions (list[str]),",
            "recent_capability_changes (list[str]).",
            "",
        ]
        if existing:
            lines.append(f"Previous summary: {existing.summary}")
            lines.append("")
        lines.append("Events:")
        for ev in events[-200:]:
            lines.append(f"  [{ev.get('event_type')}] {ev.get('payload', {})}")
        return "\n".join(lines)
