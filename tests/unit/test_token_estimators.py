import sys
import types

import pytest

from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.integrations.llm.atomic_agents_engine import AtomicAgentsEngine
from adomcore.app.lifespan import build_container
from adomcore.app.settings import AppSettings
from adomcore.integrations.token.tiktoken_estimator import TiktokenEstimator
from adomcore.services.token_estimator import TokenEstimateRequest


class _FakeEncoding:
    def __init__(self, name: str) -> None:
        self.name = name

    def encode(self, text: str) -> list[int]:
        return list(
            range(len(text) if self.name == "char_based" else max(len(text) // 2, 0))
        )


@pytest.mark.asyncio
async def test_tiktoken_estimator_uses_request_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _get_encoding(name: str) -> _FakeEncoding:
        return _FakeEncoding(name)

    fake_module = types.SimpleNamespace(
        Encoding=_FakeEncoding,
        get_encoding=_get_encoding,
    )
    monkeypatch.setitem(sys.modules, "tiktoken", fake_module)

    estimator = TiktokenEstimator()

    default_result = await estimator.estimate(
        TokenEstimateRequest(text="abcd", model_id="gpt4o")
    )
    configured_result = await estimator.estimate(
        TokenEstimateRequest(
            text="abcd",
            model_id="gpt4o",
            config={"encoding_name": "char_based"},
        )
    )

    assert default_result.token_count == 2
    assert configured_result.token_count == 4


@pytest.mark.asyncio
async def test_build_container_loads_token_estimate_config() -> None:
    settings = AppSettings(
        default_model_id="gpt4o",
        models=[
            {
                "id": "main",
                "provider": "openai_compatible",
                "model": "gpt-4o-mini",
                "token_estimate_provider": "heuristic",
                "context_window": 32000,
            },
            {
                "id": "gpt4o",
                "provider": "openai_compatible",
                "model": "gpt-4o",
                "token_estimate_provider": "tiktoken",
                "token_estimate_config": {"encoding_name": "o200k_base"},
                "context_window": 128000,
            },
        ],
    )

    container = await build_container(settings)
    spec = container.model_service.get("gpt4o")

    assert spec.token_estimate_config == {"encoding_name": "o200k_base"}


@pytest.mark.asyncio
async def test_build_container_loads_extra_config() -> None:
    settings = AppSettings(
        default_model_id="gpt4o",
        models=[
            {
                "id": "main",
                "provider": "openai_compatible",
                "model": "gpt-4o-mini",
                "context_window": 32000,
            },
            {
                "id": "gpt4o",
                "provider": "openai_compatible",
                "model": "gpt-4o",
                "extra_config": {"reasoning_effort": "medium"},
                "context_window": 128000,
            },
        ],
    )

    container = await build_container(settings)
    spec = container.model_service.get("gpt4o")

    assert spec.extra_config == {"reasoning_effort": "medium"}


@pytest.mark.asyncio
async def test_openai_engine_passes_extra_config_to_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeMessage:
        tool_calls = None
        content = "ok"

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeResponse:
        choices = [_FakeChoice()]

    class _FakeCompletions:
        async def create(self, **kwargs: object) -> _FakeResponse:
            captured.update(kwargs)
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.chat = _FakeChat()

    fake_module = types.SimpleNamespace(AsyncOpenAI=_FakeAsyncOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    engine = AtomicAgentsEngine(
        ModelSpec(
            id="gpt4o",
            provider=ModelProviderKind.OPENAI_COMPATIBLE,
            model="gpt-4o",
            context_window=128000,
            extra_config={"reasoning_effort": "medium"},
        )
    )

    await engine.decide({"messages": [{"role": "user", "content": "hi"}]})

    assert captured["reasoning_effort"] == "medium"
