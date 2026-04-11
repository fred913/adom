"""Model client factory — routes by ModelProviderKind."""

from adomcore.domain.models import ModelProviderKind, ModelSpec


def make_client(spec: ModelSpec) -> object:
    if spec.provider == ModelProviderKind.ANTHROPIC:
        from adomcore.integrations.llm.anthropic_client_factory import (
            make_anthropic_client,
        )

        return make_anthropic_client(spec)
    from adomcore.integrations.llm.openai_compatible_client_factory import (
        make_openai_compatible_client,
    )

    return make_openai_compatible_client(spec)
