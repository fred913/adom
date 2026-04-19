from collections.abc import AsyncIterator, Iterator

import pytest

from adomcore.domain.capabilities import FunctionSpec
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import (
    ToolExecutor,
    ToolFinalUpdate,
    ToolProgressUpdate,
)


async def _async_streaming_tool() -> AsyncIterator[dict[str, object]]:
    yield {"kind": "progress", "payload": {"message": "step 1"}}
    yield {"kind": "progress", "payload": {"message": "step 2"}}
    yield {"kind": "final", "result": {"status": "ok"}}


def _sync_streaming_tool() -> Iterator[object]:
    yield "warming up"
    yield ToolFinalUpdate(kind="final", result={"status": "done"})


@pytest.mark.asyncio
async def test_tool_executor_execute_stream_supports_async_generators() -> None:
    registry = CapabilityRegistry()
    registry.register(
        FunctionSpec(
            name="stream_async",
            description="",
            input_schema={"type": "object", "properties": {}},
        ),
        _async_streaming_tool,
    )
    executor = ToolExecutor(registry)

    updates = [update async for update in executor.execute_stream("stream_async", {})]

    assert updates == [
        ToolProgressUpdate(kind="progress", payload={"message": "step 1"}),
        ToolProgressUpdate(kind="progress", payload={"message": "step 2"}),
        ToolFinalUpdate(kind="final", result={"status": "ok"}),
    ]


@pytest.mark.asyncio
async def test_tool_executor_execute_returns_final_result_for_streaming_tools() -> None:
    registry = CapabilityRegistry()
    registry.register(
        FunctionSpec(
            name="stream_sync",
            description="",
            input_schema={"type": "object", "properties": {}},
        ),
        _sync_streaming_tool,
    )
    executor = ToolExecutor(registry)

    result = await executor.execute("stream_sync", {})

    assert result == {"status": "done"}
