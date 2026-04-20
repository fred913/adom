"""Domain models for LLM provider and model specifications."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _empty_json_object() -> dict[str, Any]:
    return {}


class ModelProviderKind(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class TokenEstimateProviderKind(StrEnum):
    TIKTOKEN = "tiktoken"
    ANTHROPIC_COUNT_TOKENS = "anthropic_count_tokens"
    HEURISTIC = "heuristic"


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    extra_config: dict[str, Any] = Field(default_factory=_empty_json_object)
    token_estimate_provider: TokenEstimateProviderKind = (
        TokenEstimateProviderKind.HEURISTIC
    )
    token_estimate_config: dict[str, Any] = Field(default_factory=_empty_json_object)


type ModelSpec_Anthropic = ModelSpec
type ModelSpec_OpenAICompatible = ModelSpec
