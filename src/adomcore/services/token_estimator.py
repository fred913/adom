"""Token estimator protocol and request/result types."""

from typing import Any, Protocol, runtime_checkable

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class TokenEstimateRequest:
    text: str
    model_id: str
    config: dict[str, Any] | None = None


@dataclass(frozen=True)
class TokenEstimateResult:
    token_count: int
    provider: str


@runtime_checkable
class TokenEstimator(Protocol):
    async def estimate(self, request: TokenEstimateRequest) -> TokenEstimateResult: ...
