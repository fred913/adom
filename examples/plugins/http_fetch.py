"""Plugin example: async HTTP fetch tool."""

import asyncio

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.plugins.base import BasePlugin
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor


async def fetch_url(url: str) -> dict[str, object]:
    import urllib.request

    with urllib.request.urlopen(url, timeout=5) as r:
        return {"status": r.status, "body": r.read(512).decode(errors="replace")}


class HttpFetchPlugin(BasePlugin):
    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="fetch_url",
                    description="Fetch the first 512 bytes of a URL.",
                    input_schema={
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                    source_plugin=self.id,
                ),
                handler=fetch_url,
            )
        ]


async def main() -> None:
    registry = CapabilityRegistry()
    plugin = HttpFetchPlugin(
        plugin_id="http_fetch",
        name="HTTP Fetch",
        description="Fetch the first bytes from a URL.",
    )
    for binding in plugin.functions():
        registry.register(binding.spec, binding.handler)
    executor = ToolExecutor(registry)
    result = await executor.execute("fetch_url", {"url": "https://example.com"})
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
