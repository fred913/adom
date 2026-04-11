"""Plugin example: register a simple calculator tool."""

import asyncio

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import PluginId
from adomcore.plugins.context import PluginContext
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor


def add(a: float, b: float) -> dict[str, float]:
    return {"result": a + b}


def setup(ctx: PluginContext) -> None:
    ctx.register_function(
        FunctionSpec(
            name="add",
            description="Add two numbers.",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
            source_plugin=PluginId("calculator"),
        ),
        add,
    )


async def main() -> None:
    registry = CapabilityRegistry()
    setup(PluginContext(registry))
    executor = ToolExecutor(registry)
    print(await executor.execute("add", {"a": 3, "b": 4}))


if __name__ == "__main__":
    asyncio.run(main())
