"""Anthropic client factory."""

from adomcore.domain.models import ModelSpec


def make_anthropic_client(spec: ModelSpec) -> object:
    import anthropic

    return anthropic.AsyncAnthropic(api_key=spec.api_key or "")
