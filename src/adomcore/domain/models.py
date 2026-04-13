"""Domain models for LLM provider and model specifications."""

from dataclasses import field
from enum import StrEnum
from typing import Any, Literal

from pydantic.dataclasses import dataclass


class ModelProviderKind(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class TokenEstimateProviderKind(StrEnum):
    TIKTOKEN = "tiktoken"
    ANTHROPIC_COUNT_TOKENS = "anthropic_count_tokens"
    HEURISTIC = "heuristic"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: ModelProviderKind
    model: str
    context_window: int
    supports_tools: bool = True
    supports_structured_output: bool = True
    supports_streaming: bool = True
    enabled: bool = True
    api_base: str | None = None
    api_key: str | None = None
    extra_config: dict[str, Any] = field(default_factory=lambda: {})
    token_estimate_provider: TokenEstimateProviderKind = (
        TokenEstimateProviderKind.HEURISTIC
    )
    token_estimate_config: dict[str, Any] = field(default_factory=lambda: {})


class ModelSpec_Anthropic(ModelSpec):
    provider: Literal[ModelProviderKind.ANTHROPIC] = ModelProviderKind.ANTHROPIC


class ModelSpec_OpenAICompatible(ModelSpec):
    provider: Literal[ModelProviderKind.OPENAI_COMPATIBLE] = (
        ModelProviderKind.OPENAI_COMPATIBLE
    )
