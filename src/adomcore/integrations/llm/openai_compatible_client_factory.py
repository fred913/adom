"""OpenAI-compatible client factory."""

from adomcore.domain.models import ModelSpec


def make_openai_compatible_client(spec: ModelSpec) -> object:
    import openai

    return openai.AsyncOpenAI(
        api_key=spec.api_key or "none",
        base_url=spec.api_base or "http://localhost:11434/v1",
    )
