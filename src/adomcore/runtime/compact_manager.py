"""CompactManager — decide if compact is needed and trigger it."""

from loguru import logger

from adomcore.domain.ids import ThreadId
from adomcore.domain.policies import TokenBudgetPolicy
from adomcore.services.compact_service import CompactService
from adomcore.storage.stores.thread_store import ThreadStore


class CompactManager:
    def __init__(
        self,
        thread_store: ThreadStore,
        compact_service: CompactService,
        policy: TokenBudgetPolicy,
    ) -> None:
        self._threads = thread_store
        self._compact_svc = compact_service
        self._policy = policy

    async def maybe_compact(
        self, tid: ThreadId, estimated_tokens: int, context_window: int
    ) -> bool:
        ratio = estimated_tokens / max(context_window, 1)
        if ratio >= self._policy.hard_ratio:
            logger.info("Hard compact threshold reached for thread {}", tid)
            await self._compact_svc.compact(tid)
            return True
        if ratio >= self._policy.soft_ratio:
            logger.info("Soft compact threshold reached for thread {}", tid)
            await self._compact_svc.compact(tid)
            return True
        return False
