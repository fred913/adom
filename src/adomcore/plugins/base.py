"""Plugin protocol."""

from collections.abc import Awaitable
from typing import Protocol, runtime_checkable

from adomcore.plugins.context import PluginContext


@runtime_checkable
class Plugin(Protocol):
    def setup(self, ctx: PluginContext) -> None | Awaitable[None]: ...
