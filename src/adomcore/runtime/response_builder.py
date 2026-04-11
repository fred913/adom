"""TurnResult and TurnResultBuilder."""

from typing import Any

from pydantic.dataclasses import dataclass


@dataclass
class TurnResult:
    response_text: str
    thread_id: str
    steps: int
    tool_calls: list[dict[str, Any]]


class TurnResultBuilder:
    def __init__(self) -> None:
        self._response_text = ""
        self._thread_id = ""
        self._steps = 0
        self._tool_calls: list[dict[str, Any]] = []

    def set_response(self, text: str) -> None:
        self._response_text = text

    def set_thread_id(self, tid: str) -> None:
        self._thread_id = tid

    def increment_steps(self) -> None:
        self._steps += 1

    def add_tool_call(self, name: str, result: Any) -> None:
        self._tool_calls.append({"name": name, "result": result})

    def add_tool_call_record(self, record: dict[str, Any]) -> None:
        self._tool_calls.append(record)

    def build(self) -> TurnResult:
        return TurnResult(
            response_text=self._response_text,
            thread_id=self._thread_id,
            steps=self._steps,
            tool_calls=self._tool_calls,
        )
