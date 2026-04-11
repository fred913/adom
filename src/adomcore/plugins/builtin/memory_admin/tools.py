"""Builtin memory_admin plugin — compact memory tools."""

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("memory_admin")
type _StatusResult = dict[str, str]


def _force_compact(thread_id: str) -> _StatusResult:
    return {"status": "compacted", "thread_id": thread_id}


def _inspect_compact_memory(thread_id: str) -> _StatusResult:
    return {"status": "ok", "thread_id": thread_id}


def memory_admin_function_bindings() -> list[FunctionBinding]:
    return [
        FunctionBinding(
            spec=FunctionSpec(
                name="force_compact",
                description="Force a compact of the current thread's memory.",
                input_schema={
                    "type": "object",
                    "properties": {"thread_id": {"type": "string"}},
                    "required": ["thread_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_force_compact,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="inspect_compact_memory",
                description="Inspect the current compact memory snapshot.",
                input_schema={
                    "type": "object",
                    "properties": {"thread_id": {"type": "string"}},
                    "required": ["thread_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_inspect_compact_memory,
        ),
    ]
