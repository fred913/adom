"""Model client factory — routes by ModelProviderKind."""

from typing import overload

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from adomcore.domain.models import (
    ModelProviderKind,
    ModelSpec,
    ModelSpec_Anthropic,
    ModelSpec_OpenAICompatible,
)


@overload  # basically a best-effort type annotation
def make_client(spec: ModelSpec_Anthropic) -> AsyncAnthropic: ...
@overload
def make_client(spec: ModelSpec_OpenAICompatible) -> AsyncOpenAI: ...
@overload
def make_client(spec: ModelSpec) -> AsyncAnthropic | AsyncOpenAI: ...


def make_client(spec: ModelSpec) -> AsyncAnthropic | AsyncOpenAI:
    if spec.provider == ModelProviderKind.ANTHROPIC:
        from adomcore.integrations.llm.anthropic_client_factory import (
            make_anthropic_client,
        )

        return make_anthropic_client(spec)
    from adomcore.integrations.llm.openai_compatible_client_factory import (
        make_openai_compatible_client,
    )

    return make_openai_compatible_client(spec)
