"""Tool executor — execute local function-provider callables."""

import inspect
import json
from typing import Any

from loguru import logger

from adomcore.services.capability_registry import CapabilityRegistry


class ToolExecutionError(Exception):
    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        self.detail = detail
        super().__init__(f"Tool {name!r} failed: {detail}")


class ToolExecutor:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    async def execute(self, function_name: str, arguments: dict[str, Any]) -> Any:
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
            json.dumps(arguments, default=str)[:200],
        )
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            return result
        except Exception as exc:
            raise ToolExecutionError(function_name, str(exc)) from exc
