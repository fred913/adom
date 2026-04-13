"""Plugin-facing model gateway and handles."""

import json
from typing import Any, cast

from anthropic import AsyncAnthropic
from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.integrations.llm.model_client_factory import make_client
from adomcore.services.model_service import ModelService


class PluginModelHandle:
    def __init__(self, spec: ModelSpec) -> None:
        self._spec = spec
        self._client = make_client(spec)

    @property
    def spec(self) -> ModelSpec:
        return self._spec

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        if self._spec.provider == ModelProviderKind.ANTHROPIC:
            kwargs: dict[str, Any] = {
                "model": self._spec.model,
                "max_tokens": 2048,
            }
            if system:
                kwargs["system"] = system
            kwargs.update(self._spec.extra_config)
            assert isinstance(self._client, AsyncAnthropic)
            resp = await self._client.messages.create(
                **kwargs,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            text_parts = [
                block.text
                for block in cast(list[Any], resp.content)
                if block.type == "text"
            ]
            return "".join(cast(list[str], text_parts))

        messages: list[ChatCompletionMessageParam] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        assert isinstance(self._client, AsyncOpenAI)
        resp = await self._client.chat.completions.create(
            model=self._spec.model,
            messages=messages,
            **self._spec.extra_config,
            stream=False,
        )
        return resp.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> dict[str, Any]:
        effective_system = (
            f"{system}\n\nReturn only a valid JSON object."
            if system
            else "Return only a valid JSON object."
        )
        text = await self.generate_text(prompt, system=effective_system)
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(clean))
        except json.JSONDecodeError:
            logger.warning(
                "plugin model gateway: could not parse JSON from model response"
            )
            return {"raw": text}


class PluginModelGateway:
    def __init__(self, model_service: ModelService) -> None:
        self._model_service = model_service

    @property
    def model_service(self) -> ModelService:
        return self._model_service

    def get_model(self, model_id: str | None = None) -> PluginModelHandle:
        spec = (
            self._model_service.get_default()
            if model_id is None
            else self._model_service.get(model_id)
        )
        return PluginModelHandle(spec)
