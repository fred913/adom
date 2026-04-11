"""Plugin example: async HTTP fetch tool."""

import asyncio

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import PluginId
from adomcore.plugins.context import PluginContext
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor


async def fetch_url(url: str) -> dict[str, object]:
    import urllib.request

    with urllib.request.urlopen(url, timeout=5) as r:
        return {"status": r.status, "body": r.read(512).decode(errors="replace")}


def setup(ctx: PluginContext) -> None:
    ctx.register_function(
        FunctionSpec(
            name="fetch_url",
            description="Fetch the first 512 bytes of a URL.",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            source_plugin=PluginId("http_fetch"),
        ),
        fetch_url,
    )


async def main() -> None:
    registry = CapabilityRegistry()
    setup(PluginContext(registry))
    executor = ToolExecutor(registry)
    result = await executor.execute("fetch_url", {"url": "https://example.com"})
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
