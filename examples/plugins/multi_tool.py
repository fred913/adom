"""Plugin example: register multiple tools from one plugin.

Demonstrates a plugin that contributes an entire category of related
tools (file read, file write, file list).
"""

import asyncio
import os
from pathlib import Path

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.plugins.base import BasePlugin
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor


def read_file(path: str) -> dict[str, str]:
    return {"content": Path(path).read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict[str, str]:
    Path(path).write_text(content, encoding="utf-8")
    return {"status": "written", "path": path}


def list_dir(path: str = ".") -> dict[str, list[str]]:
    return {"entries": os.listdir(path)}


class LocalFsPlugin(BasePlugin):
    plugin_id = "local_fs"
    plugin_name = "Local FS"
    plugin_description = "Local filesystem example plugin."

    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="read_file",
                    description="Read a local text file.",
                    input_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                    source_plugin=self.id,
                ),
                handler=read_file,
            ),
            FunctionBinding(
                spec=FunctionSpec(
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
                    source_plugin=self.id,
                ),
                handler=write_file,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="list_dir",
                    description="List entries in a directory.",
                    input_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string", "default": "."}},
                    },
                    source_plugin=self.id,
                ),
                handler=list_dir,
            ),
        ]


async def main() -> None:
    registry = CapabilityRegistry()
    plugin = LocalFsPlugin()
    for binding in plugin.functions():
        registry.register(binding.spec, binding.handler)
    executor = ToolExecutor(registry)

    print("Tools registered:", [s.name for s in registry.list_all()])
    print(await executor.execute("list_dir", {"path": "."}))


if __name__ == "__main__":
    asyncio.run(main())
