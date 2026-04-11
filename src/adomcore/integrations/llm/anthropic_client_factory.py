"""Anthropic client factory."""

from anthropic import AsyncAnthropic

from adomcore.domain.models import ModelSpec


def make_anthropic_client(spec: ModelSpec) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=spec.api_key or "")
