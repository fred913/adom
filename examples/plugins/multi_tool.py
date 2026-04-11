"""Plugin example: register multiple tools from one plugin.

Demonstrates a plugin that contributes an entire category of related
tools (file read, file write, file list).
"""

import asyncio
import os
from pathlib import Path

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import PluginId
from adomcore.plugins.context import PluginContext
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor

_PID = PluginId("local_fs")


def read_file(path: str) -> dict[str, str]:
    return {"content": Path(path).read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict[str, str]:
    Path(path).write_text(content, encoding="utf-8")
    return {"status": "written", "path": path}


def list_dir(path: str = ".") -> dict[str, list[str]]:
    return {"entries": os.listdir(path)}


def setup(ctx: PluginContext) -> None:
    ctx.register_function(
        FunctionSpec(
            name="read_file",
            description="Read a local text file.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            source_plugin=_PID,
        ),
        read_file,
    )
    ctx.register_function(
        FunctionSpec(
            name="write_file",
            description="Write text content to a local file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            source_plugin=_PID,
        ),
        write_file,
    )
    ctx.register_function(
        FunctionSpec(
            name="list_dir",
            description="List entries in a directory.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
            source_plugin=_PID,
        ),
        list_dir,
    )


async def main() -> None:
    registry = CapabilityRegistry()
    setup(PluginContext(registry))
    executor = ToolExecutor(registry)

    print("Tools registered:", [s.name for s in registry.list_all()])
    print(await executor.execute("list_dir", {"path": "."}))


if __name__ == "__main__":
    asyncio.run(main())
