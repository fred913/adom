"""Tool executor — execute local function-provider callables."""

import asyncio
import inspect
import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, Literal, cast

from loguru import logger

from adomcore.services.capability_registry import CapabilityRegistry


class ToolExecutionError(Exception):
    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        self.detail = detail
        super().__init__(f"Tool {name!r} failed: {detail}")


@dataclass(frozen=True)
class ToolProgressUpdate:
    kind: Literal["progress"]
    payload: dict[str, Any]


@dataclass(frozen=True)
class ToolFinalUpdate:
    kind: Literal["final"]
    result: Any


type ToolExecutionUpdate = ToolProgressUpdate | ToolFinalUpdate


class ToolExecutor:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    async def execute(self, function_name: str, arguments: dict[str, Any]) -> Any:
        final_result: Any | None = None
        got_final = False
        async for update in self.execute_stream(function_name, arguments):
            if isinstance(update, ToolFinalUpdate):
                final_result = update.result
                got_final = True
        if not got_final:
            raise ToolExecutionError(
                function_name, "Tool stream ended without final result"
            )
        return final_result

    async def execute_stream(
        self, function_name: str, arguments: dict[str, Any]
    ) -> AsyncIterator[ToolExecutionUpdate]:
        handler = self._registry.get_handler(function_name)
        if handler is None:
            raise ToolExecutionError(
                function_name, f"No handler registered for {function_name!r}"
            )
        spec = self._registry.get_spec(function_name)
        if spec is not None and not spec.enabled:
            raise ToolExecutionError(
                function_name, f"Function {function_name!r} is disabled"
            )

        logger.debug(
            "Executing tool: {} with args: {}",
            function_name,
            json.dumps(arguments, default=str),
        )
        try:
            if inspect.isasyncgenfunction(handler):
                async for update in self._consume_async_iterable(
                    function_name, handler(**arguments)
                ):
                    yield update
                return
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = await asyncio.to_thread(handler, **arguments)

            if inspect.isasyncgen(result):
                async for update in self._consume_async_iterable(function_name, result):
                    yield update
                return
            if inspect.isgenerator(result) or isinstance(result, Iterator):
                async for update in self._consume_sync_iterable(
                    function_name, cast(Iterator[Any], result)
                ):
                    yield update
                return

            logger.debug(
                "Tool response: {} -> {}",
                function_name,
                json.dumps(result, default=str),
            )
            yield ToolFinalUpdate(kind="final", result=result)
        except Exception as exc:
            raise ToolExecutionError(function_name, str(exc)) from exc

    async def _consume_async_iterable(
        self, function_name: str, iterable: AsyncIterator[Any]
    ) -> AsyncIterator[ToolExecutionUpdate]:
        saw_final = False
        async for item in iterable:
            update = self._normalize_stream_item(function_name, item)
            if isinstance(update, ToolFinalUpdate):
                saw_final = True
            yield update
        if not saw_final:
            raise ToolExecutionError(
                function_name,
                "Streaming tool must yield a final result event before completion",
            )

    async def _consume_sync_iterable(
        self, function_name: str, iterable: Iterator[Any]
    ) -> AsyncIterator[ToolExecutionUpdate]:
        saw_final = False
        while True:
            item, done = await asyncio.to_thread(self._next_sync_item, iterable)
            if done:
                break
            update = self._normalize_stream_item(function_name, item)
            if isinstance(update, ToolFinalUpdate):
                saw_final = True
            yield update
        if not saw_final:
            raise ToolExecutionError(
                function_name,
                "Streaming tool must yield a final result event before completion",
            )

    @staticmethod
    def _next_sync_item(iterable: Iterator[Any]) -> tuple[Any | None, bool]:
        try:
            return next(iterable), False
        except StopIteration:
            return None, True

    def _normalize_stream_item(
        self, function_name: str, item: Any
    ) -> ToolExecutionUpdate:
        if isinstance(item, ToolProgressUpdate | ToolFinalUpdate):
            return item
        if isinstance(item, dict):
            d = cast(dict[str, Any], item)
            kind = d.get("kind")
            if kind == "progress":
                payload = d.get("payload")
                if not isinstance(payload, dict):
                    payload = {key: value for key, value in d.items() if key != "kind"}
                return ToolProgressUpdate(
                    kind="progress", payload=cast(dict[str, Any], payload)
                )
            if kind in {"final", "final_result"}:
                return ToolFinalUpdate(kind="final", result=d.get("result"))
        if isinstance(item, str):
            return ToolProgressUpdate(kind="progress", payload={"message": item})
        raise ToolExecutionError(
            function_name,
            "Unsupported streaming item. Expected progress/final event dict or Tool*Update instance.",
        )
