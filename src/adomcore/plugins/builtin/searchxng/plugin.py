"""Builtin SearchXNG plugin."""

from typing import Any

from adomcore.domain.capabilities import FunctionBinding
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.searchxng.tools import SearchXNGToolset


class BuiltinSearchXNGPlugin(BasePlugin):
    plugin_id = "searchxng"
    plugin_name = "searchxng"
    plugin_description = "Search tools backed by a configured SearchXNG/SearXNG instance."

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._tools = SearchXNGToolset(config)

    def functions(self) -> list[FunctionBinding]:
        return self._tools.function_bindings()


plugin = BuiltinSearchXNGPlugin