"""Runtime policy types."""

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class TokenBudgetPolicy:
    soft_ratio: float = 0.75
    hard_ratio: float = 0.9
    recent_messages_window: int = 24


@dataclass(frozen=True)
class PluginTrustPolicy:
    allow_builtin: bool = True
    allow_local: bool = True
    allow_remote: bool = False


@dataclass(frozen=True)
class MutationPolicy:
    allow_self_mutation: bool = True
    require_confirmation: bool = False
