"""Function and capability specifications."""

from collections.abc import Callable

from pydantic.dataclasses import dataclass

from adomcore.domain.ids import PluginId
from adomcore.utils import StructuredValue

# Tool handlers are intentionally typed wider than ``StructuredValue`` because
# the runtime accepts sync handlers, async handlers, and streaming handlers, then
# validates/normalizes their yielded or returned values in ``ToolExecutor``.
type FunctionHandler = Callable[..., object]


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    description: str
    input_schema: dict[str, StructuredValue]
    output_schema: dict[str, StructuredValue] | None = None
    handler_ref: str | None = None
    source_plugin: PluginId | None = None
    enabled: bool = True


@dataclass(frozen=True)
class FunctionBinding:
    spec: FunctionSpec
    handler: FunctionHandler


@dataclass(frozen=True)
class CapabilityRef:
    kind: str  # "function" | "skill" | "mcp_tool"
    name: str
    source: str  # plugin id or mcp server id
