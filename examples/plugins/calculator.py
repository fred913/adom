"""Plugin example: declare a simple calculator tool."""

import asyncio

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.plugins.base import BasePlugin
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor


def add(a: float, b: float) -> dict[str, float]:
    return {"result": a + b}


class CalculatorPlugin(BasePlugin):
    plugin_id = "calculator"
    plugin_name = "Calculator"
    plugin_description = "A simple calculator example plugin."

    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
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
                    source_plugin=self.id,
                ),
                handler=add,
            )
        ]


async def main() -> None:
    registry = CapabilityRegistry()
    plugin = CalculatorPlugin()
    for binding in plugin.functions():
        registry.register(binding.spec, binding.handler)
    executor = ToolExecutor(registry)
    print(await executor.execute("add", {"a": 3, "b": 4}))


if __name__ == "__main__":
    asyncio.run(main())
