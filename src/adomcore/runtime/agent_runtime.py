"""AgentRuntime — the single brain. Owns run_user_turn and run_timer_turn."""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

from adomcore.domain.actions import CallFunctionAction, RespondAction
from adomcore.domain.events import EventEnvelope
from adomcore.domain.ids import CronJobId, ThreadId
from adomcore.domain.streaming import (
    EngineDecisionEvent,
    EngineTextDeltaEvent,
    EngineToolCallDeltaEvent,
    TurnStreamEvent,
    TurnStreamEventType,
)
from adomcore.runtime.action_router import ActionExecutionResult, ActionRouter
from adomcore.runtime.compact_manager import CompactManager
from adomcore.runtime.context_builder import ContextBuilder
from adomcore.runtime.response_builder import (
    ToolCallRecord,
    TurnResult,
    TurnResultBuilder,
)
from adomcore.services.agent_service import AgentService
from adomcore.services.tool_executor import ToolProgressUpdate
from adomcore.storage.stores.thread_store import ThreadStore
from adomcore.utils import StructuredValue, require_json_object, require_json_value


def _new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


class AgentRuntime:
    def __init__(
        self,
        agent_service: AgentService,
        thread_store: ThreadStore,
        context_builder: ContextBuilder,
        action_router: ActionRouter,
        compact_manager: CompactManager,
        engine: object,
        max_loop_steps: int = 8,
    ) -> None:
        self._agent = agent_service
        self._threads = thread_store
        self._ctx_builder = context_builder
        self._router = action_router
        self._compact = compact_manager
        self._engine = engine
        self._max_steps = max_loop_steps

    async def _append_tool_call_event(
        self, thread_id: ThreadId, action: CallFunctionAction
    ) -> None:
        await self._append(
            thread_id,
            "assistant_tool_call",
            {
                "call_id": action.call_id,
                "tool_name": action.function_name,
                "arguments": action.arguments,
            },
        )

    async def _append_tool_progress_event(
        self,
        thread_id: ThreadId,
        action: CallFunctionAction,
        payload: dict[str, StructuredValue],
    ) -> None:
        await self._append(
            thread_id,
            "tool_progress",
            {
                "call_id": action.call_id,
                "tool_name": action.function_name,
                **payload,
            },
        )

    async def _summarise_tool_progress(
        self,
        action: CallFunctionAction,
        payload: dict[str, StructuredValue],
    ) -> str | None:
        from adomcore.integrations.llm.engine_protocol import AgentEngine

        assert isinstance(self._engine, AgentEngine)
        prompt = (
            "Summarise the latest tool progress for the user in one short sentence. "
            'Return JSON with shape {"summary": string}.\n'
            f"Tool name: {action.function_name}\n"
            f"Call id: {action.call_id}\n"
            f"Latest progress payload: {json.dumps(payload, ensure_ascii=False, default=str)}"
        )
        raw = await self._engine.summarise(prompt)
        summary = raw.get("summary")
        if not isinstance(summary, str):
            return None
        clean = summary.strip()
        return clean or None

    async def _execute_function_action(
        self,
        thread_id: ThreadId,
        action: CallFunctionAction,
        on_event: Callable[[TurnStreamEvent], Awaitable[None]] | None = None,
    ) -> tuple[StructuredValue | None, bool]:
        last_summary: str | None = None
        final_result: StructuredValue | None = None
        final_is_error = False

        try:
            async for update in self._router.route_function_stream(action):
                if isinstance(update, ToolProgressUpdate):
                    progress_payload = {
                        "payload": update.payload,
                        **update.payload,
                    }
                    progress_payload = require_json_object(progress_payload)
                    await self._append_tool_progress_event(
                        thread_id, action, progress_payload
                    )
                    if on_event is not None:
                        await on_event(
                            TurnStreamEvent(
                                event=TurnStreamEventType.TOOL_PROGRESS,
                                data={
                                    "call_id": action.call_id,
                                    "tool_name": action.function_name,
                                    **progress_payload,
                                    "thread_id": str(thread_id),
                                },
                            )
                        )
                    summary = await self._summarise_tool_progress(
                        action, update.payload
                    )
                    if summary and summary != last_summary:
                        last_summary = summary
                        await self._append(
                            thread_id,
                            "assistant_progress",
                            {
                                "call_id": action.call_id,
                                "tool_name": action.function_name,
                                "text": summary,
                            },
                        )
                        if on_event is not None:
                            await on_event(
                                TurnStreamEvent(
                                    event=TurnStreamEventType.TOOL_PROGRESS_SUMMARY,
                                    data={
                                        "call_id": action.call_id,
                                        "tool_name": action.function_name,
                                        "text": summary,
                                        "thread_id": str(thread_id),
                                    },
                                )
                            )
                    continue

                final_result = update.result
        except Exception as exc:
            final_is_error = True
            final_result = str(exc)

        return final_result, final_is_error

    async def run_user_turn(self, thread_id: ThreadId, text: str) -> TurnResult:
        self._threads.ensure_thread_dir(thread_id)
        await self._append(thread_id, "user_message", {"text": text})
        return await self._run_loop(thread_id)

    async def run_user_turn_stream(
        self, thread_id: ThreadId, text: str
    ) -> AsyncIterator[TurnStreamEvent]:
        self._threads.ensure_thread_dir(thread_id)
        await self._append(thread_id, "user_message", {"text": text})
        async for event in self._run_loop_stream(thread_id):
            yield event

    async def run_timer_turn(
        self, thread_id: ThreadId, instruction_text: str, job_id: CronJobId
    ) -> TurnResult:
        self._threads.ensure_thread_dir(thread_id)
        await self._append(
            thread_id,
            "system_event",
            {
                "event_kind": "timer_fired",
                "job_id": str(job_id),
                "instruction": instruction_text,
            },
        )
        return await self._run_loop(thread_id)

    async def _run_loop(self, thread_id: ThreadId) -> TurnResult:
        from adomcore.integrations.llm.engine_protocol import AgentEngine

        assert isinstance(self._engine, AgentEngine)

        state = self._agent.load()
        builder = TurnResultBuilder()
        builder.set_thread_id(str(thread_id))

        for _ in range(self._max_steps):
            ctx = self._ctx_builder.build(
                thread_id=str(thread_id),
                active_model_id=state.active_model_id,
            )

            await self._compact.maybe_compact(
                thread_id,
                ctx.estimated_tokens,
                ctx.model_spec.context_window,
            )

            decision = await self._engine.decide(
                {
                    "system": ctx.system_prompt,
                    "messages": ctx.messages,
                    "tools": ctx.tools,
                }
            )

            builder.increment_steps()
            final_text: str | None = None

            for action in decision.actions:
                if isinstance(action, CallFunctionAction):
                    await self._append_tool_call_event(thread_id, action)
                    tool_result, is_error = await self._execute_function_action(
                        thread_id, action
                    )
                    result = ActionExecutionResult(
                        action=action, result=tool_result, is_error=is_error
                    )
                else:
                    result = await self._router.route(action)
                if isinstance(action, RespondAction):
                    final_text = action.text
                    await self._append(
                        thread_id, "assistant_message", {"text": action.text}
                    )
                else:
                    builder.add_tool_call(str(type(action).__name__), result.result)
                    await self._append(
                        thread_id,
                        "tool_result",
                        {
                            "action": type(action).__name__,
                            "call_id": getattr(action, "call_id", ""),
                            "tool_name": getattr(action, "function_name", None),
                            "arguments": getattr(action, "arguments", None),
                            "result": str(result.result),
                            "is_error": result.is_error,
                        },
                    )

            if final_text is not None:
                builder.set_response(final_text)
                break

        return builder.build()

    async def _run_loop_stream(
        self, thread_id: ThreadId
    ) -> AsyncIterator[TurnStreamEvent]:
        from adomcore.integrations.llm.engine_protocol import AgentEngine

        assert isinstance(self._engine, AgentEngine)

        state = self._agent.load()
        builder = TurnResultBuilder()
        builder.set_thread_id(str(thread_id))
        streamed_text: list[str] = []
        seen_tool_calls: set[str] = set()

        for _ in range(self._max_steps):
            ctx = self._ctx_builder.build(
                thread_id=str(thread_id),
                active_model_id=state.active_model_id,
            )

            await self._compact.maybe_compact(
                thread_id,
                ctx.estimated_tokens,
                ctx.model_spec.context_window,
            )

            decision_event: EngineDecisionEvent | None = None
            async for engine_event in self._engine.stream_decide(
                {
                    "system": ctx.system_prompt,
                    "messages": ctx.messages,
                    "tools": ctx.tools,
                }
            ):
                if isinstance(engine_event, EngineTextDeltaEvent):
                    streamed_text.append(engine_event.text)
                    yield TurnStreamEvent(
                        event=TurnStreamEventType.ASSISTANT_TEXT_DELTA,
                        data={"text": engine_event.text, "thread_id": str(thread_id)},
                    )
                elif isinstance(engine_event, EngineToolCallDeltaEvent):
                    if engine_event.call_id not in seen_tool_calls:
                        seen_tool_calls.add(engine_event.call_id)
                        yield TurnStreamEvent(
                            event=TurnStreamEventType.TOOL_CALL_STARTED,
                            data={
                                "call_id": engine_event.call_id,
                                "tool_name": engine_event.tool_name,
                                "thread_id": str(thread_id),
                            },
                        )
                    yield TurnStreamEvent(
                        event=TurnStreamEventType.TOOL_CALL_DELTA,
                        data={
                            "call_id": engine_event.call_id,
                            "tool_name": engine_event.tool_name,
                            "arguments_delta": engine_event.arguments_delta,
                            "thread_id": str(thread_id),
                        },
                    )
                else:
                    decision_event = engine_event

            if decision_event is None:
                break

            builder.increment_steps()
            final_text: str | None = None

            for action in decision_event.decision.actions:
                if isinstance(action, CallFunctionAction):
                    if action.call_id not in seen_tool_calls:
                        yield TurnStreamEvent(
                            event=TurnStreamEventType.TOOL_CALL_STARTED,
                            data={
                                "call_id": action.call_id,
                                "tool_name": action.function_name,
                                "thread_id": str(thread_id),
                            },
                        )
                    yield TurnStreamEvent(
                        event=TurnStreamEventType.TOOL_CALL_FINISHED,
                        data={
                            "call_id": action.call_id,
                            "tool_name": action.function_name,
                            "arguments": action.arguments,
                            "thread_id": str(thread_id),
                        },
                    )
                    await self._append_tool_call_event(thread_id, action)
                    streamed_events: list[TurnStreamEvent] = []

                    async def _collect_stream_event(event: TurnStreamEvent) -> None:
                        streamed_events.append(event)

                    tool_result, is_error = await self._execute_function_action(
                        thread_id, action, _collect_stream_event
                    )
                    for stream_event in streamed_events:
                        yield stream_event
                    result = ActionExecutionResult(
                        action=action, result=tool_result, is_error=is_error
                    )
                else:
                    result = await self._router.route(action)
                if isinstance(action, RespondAction):
                    final_text = action.text
                    if not streamed_text and action.text:
                        yield TurnStreamEvent(
                            event=TurnStreamEventType.ASSISTANT_TEXT_DELTA,
                            data={"text": action.text, "thread_id": str(thread_id)},
                        )
                    await self._append(
                        thread_id, "assistant_message", {"text": action.text}
                    )
                else:
                    record = ToolCallRecord(
                        name=str(type(action).__name__),
                        call_id=getattr(action, "call_id", ""),
                        tool_name=getattr(action, "function_name", None),
                        arguments=require_json_object(getattr(action, "arguments", {}))
                        if getattr(action, "arguments", None) is not None
                        else None,
                        result=require_json_value(result.result),
                        is_error=result.is_error,
                    )
                    builder.add_tool_call_record(record)
                    yield TurnStreamEvent(
                        event=TurnStreamEventType.TOOL_RESULT,
                        data=record.model_dump(mode="json")
                        | {"thread_id": str(thread_id)},
                    )
                    await self._append(
                        thread_id,
                        "tool_result",
                        {
                            "action": type(action).__name__,
                            "call_id": getattr(action, "call_id", ""),
                            "tool_name": getattr(action, "function_name", None),
                            "arguments": getattr(action, "arguments", None),
                            "result": str(result.result),
                            "is_error": result.is_error,
                        },
                    )

            if final_text is not None:
                builder.set_response(final_text)
                yield TurnStreamEvent(
                    event=TurnStreamEventType.ASSISTANT_TEXT_DONE,
                    data={"text": final_text, "thread_id": str(thread_id)},
                )
                yield TurnStreamEvent(
                    event=TurnStreamEventType.TURN_DONE,
                    data={
                        "thread_id": str(thread_id),
                        "steps": builder.build().steps,
                        "tool_calls": [
                            tool_call.model_dump(mode="json")
                            for tool_call in builder.build().tool_calls
                        ],
                    },
                )
                break

    async def _append(
        self, thread_id: ThreadId, event_type: str, payload: dict[str, StructuredValue]
    ) -> None:
        envelope = EventEnvelope(
            event_id=_new_event_id(),
            event_type=event_type,
            ts=datetime.now(UTC),
            thread_id=thread_id,
            payload=payload,
        )
        await self._threads.append_event(envelope)
