"""AtomicAgentsEngine — default LLM engine implementation."""

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol, cast

from loguru import logger

from adomcore.domain.actions import AgentDecision, CallFunctionAction, RespondAction
from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.domain.streaming import (
    EngineDecisionEvent,
    EngineEvent,
    EngineTextDeltaEvent,
    EngineToolCallDeltaEvent,
)
from adomcore.integrations.llm.model_client_factory import make_client


class _OpenAIStreamFunctionDelta(Protocol):
    name: str | None
    arguments: str | None


class _OpenAIStreamToolCallDelta(Protocol):
    index: int
    id: str | None
    function: _OpenAIStreamFunctionDelta | None


class _OpenAIStreamDelta(Protocol):
    content: str | None
    tool_calls: list[_OpenAIStreamToolCallDelta] | None


class _OpenAIStreamChoice(Protocol):
    delta: _OpenAIStreamDelta | None


class _OpenAIStreamChunk(Protocol):
    choices: list[_OpenAIStreamChoice]


class AtomicAgentsEngine:
    def __init__(self, spec: ModelSpec) -> None:
        self._spec = spec
        self._client = make_client(spec)

    async def decide(self, context: dict[str, Any]) -> AgentDecision:
        messages = context.get("messages", [])
        tools = context.get("tools", [])

        if self._spec.provider == ModelProviderKind.ANTHROPIC:
            return await self._decide_anthropic(messages, tools, context)
        return await self._decide_openai(messages, tools, context)

    async def stream_decide(
        self, context: dict[str, Any]
    ) -> AsyncIterator[EngineEvent]:
        messages = context.get("messages", [])
        tools = context.get("tools", [])
        if self._spec.provider == ModelProviderKind.ANTHROPIC:
            decision = await self._decide_anthropic(messages, tools, context)
            yield EngineDecisionEvent(kind="decision", decision=decision)
            return
        async for event in self._stream_openai(messages, tools, context):
            yield event

    async def _decide_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> AgentDecision:
        import anthropic

        assert isinstance(self._client, anthropic.AsyncAnthropic)
        kwargs: dict[str, Any] = {
            "model": self._spec.model,
            "max_tokens": 4096,
            "messages": messages,
            "system": context.get("system", ""),
        }
        kwargs.update(self._spec.extra_config)
        if tools:
            kwargs["tools"] = tools

        resp = cast(Any, await self._client.messages.create(**kwargs))
        actions: list[Any] = []
        for block in cast(list[Any], resp.content):
            if block.type == "text":
                actions.append(RespondAction(text=cast(str, block.text)))
            elif block.type == "tool_use":
                actions.append(
                    CallFunctionAction(
                        function_name=cast(str, block.name),
                        arguments=cast(dict[str, object], dict(block.input)),
                        call_id=cast(str, block.id),
                    )
                )
        return AgentDecision(actions=cast(Any, actions))

    async def _stream_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> AsyncIterator[EngineEvent]:
        import openai

        assert isinstance(self._client, openai.AsyncOpenAI)
        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": context.get("system", "")},
                *messages,
            ],
        }
        kwargs.update(self._spec.extra_config)
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        stream = await self._client.chat.completions.create(
            **kwargs, model=self._spec.model, stream=True
        )
        text_parts: list[str] = []
        tool_names: dict[int, str] = {}
        tool_ids: dict[int, str] = {}
        tool_args: dict[int, list[str]] = {}

        async for raw_chunk in stream:
            chunk = cast(_OpenAIStreamChunk, raw_chunk)
            choices = chunk.choices
            choice = choices[0] if choices else None
            delta = choice.delta if choice else None
            if delta is None:
                continue
            content = delta.content
            if isinstance(content, str) and content:
                text_parts.append(content)
                yield EngineTextDeltaEvent(kind="assistant_text_delta", text=content)
            tool_calls = delta.tool_calls
            if not tool_calls:
                continue
            for tc in tool_calls:
                index = int(tc.index)
                tc_id = tc.id or tool_ids.get(index) or f"call_{index}"
                tool_ids[index] = tc_id
                function = tc.function
                if function is not None:
                    name = function.name
                    if name:
                        tool_names[index] = name
                    args_delta = function.arguments or ""
                    if args_delta:
                        tool_args.setdefault(index, []).append(args_delta)
                    yield EngineToolCallDeltaEvent(
                        kind="tool_call_delta",
                        call_id=tc_id,
                        tool_name=tool_names.get(index),
                        arguments_delta=args_delta,
                    )

        actions: list[Any] = []
        if tool_ids:
            for index, tc_id in tool_ids.items():
                raw_args = "".join(tool_args.get(index, [])) or "{}"
                try:
                    parsed_args = cast(dict[str, object], json.loads(raw_args))
                except json.JSONDecodeError:
                    logger.warning(
                        "stream_decide: could not parse streamed tool args: {}",
                        raw_args,
                    )
                    parsed_args = {}
                actions.append(
                    CallFunctionAction(
                        function_name=tool_names.get(index, f"tool_{index}"),
                        arguments=parsed_args,
                        call_id=tc_id,
                    )
                )
        else:
            actions.append(RespondAction(text="".join(text_parts)))

        yield EngineDecisionEvent(
            kind="decision", decision=AgentDecision(actions=cast(Any, actions))
        )

    async def _decide_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> AgentDecision:
        import openai

        assert isinstance(self._client, openai.AsyncOpenAI)
        kwargs: dict[str, Any] = {
            "model": self._spec.model,
            "messages": [
                {"role": "system", "content": context.get("system", "")},
                *messages,
            ],
        }
        kwargs.update(self._spec.extra_config)
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        resp = cast(Any, await self._client.chat.completions.create(**kwargs))
        msg = resp.choices[0].message
        actions: list[Any] = []
        if msg.tool_calls:
            from adomcore.domain.actions import CallFunctionAction

            for tc in cast(list[Any], msg.tool_calls):
                actions.append(
                    CallFunctionAction(
                        function_name=cast(str, tc.function.name),
                        arguments=cast(
                            dict[str, object],
                            json.loads(cast(str, tc.function.arguments)),
                        ),
                        call_id=cast(str, tc.id),
                    )
                )
        else:
            actions.append(RespondAction(text=cast(str, msg.content or "")))
        return AgentDecision(actions=cast(Any, actions))

    async def summarise(self, prompt: str) -> dict[str, Any]:
        if self._spec.provider == ModelProviderKind.ANTHROPIC:
            import anthropic

            assert isinstance(self._client, anthropic.AsyncAnthropic)
            resp = cast(
                Any,
                await self._client.messages.create(
                    model=self._spec.model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                    **self._spec.extra_config,
                ),
            )
            text = cast(str, resp.content[0].text) if resp.content else "{}"
            assert isinstance(text, str)
        else:
            import openai

            assert isinstance(self._client, openai.AsyncOpenAI)
            resp = cast(
                Any,
                await self._client.chat.completions.create(
                    model=self._spec.model,
                    messages=[{"role": "user", "content": prompt}],
                    **self._spec.extra_config,
                ),
            )
            text = cast(str, resp.choices[0].message.content or "{}")

        try:
            # Strip markdown code fences if present
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]

            assert isinstance(clean, str)

            return json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("summarise: could not parse JSON from model response")
            return {"summary": text}
