"""OpenAI-compatible client factory."""

from openai import AsyncOpenAI

from adomcore.domain.models import ModelSpec


def make_openai_compatible_client(spec: ModelSpec) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=spec.api_key or "none",
        base_url=spec.api_base or "http://localhost:11434/v1",
    )
