"""Builtin local_fs plugin tools."""

import os
from pathlib import Path

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("local_fs")


def read_file(path: str) -> dict[str, str]:
    return {"content": Path(path).read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict[str, str]:
    Path(path).write_text(content, encoding="utf-8")
    return {"status": "written", "path": path}


def list_dir(path: str = ".") -> dict[str, list[str]]:
    return {"entries": os.listdir(path)}


def local_fs_function_bindings() -> list[FunctionBinding]:
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
                source_plugin=_PLUGIN_ID,
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
                source_plugin=_PLUGIN_ID,
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
                source_plugin=_PLUGIN_ID,
            ),
            handler=list_dir,
        ),
    ]
