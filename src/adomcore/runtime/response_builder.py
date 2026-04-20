"""TurnResult and TurnResultBuilder."""

from pydantic import BaseModel

from adomcore.utils import StructuredValue


class ToolCallRecord(BaseModel):
    name: str
    call_id: str = ""
    tool_name: str | None = None
    arguments: dict[str, StructuredValue] | None = None
    result: StructuredValue | None = None
    is_error: bool = False


class TurnResult(BaseModel):
    response_text: str
    thread_id: str
    steps: int
    tool_calls: list[ToolCallRecord]


class TurnResultBuilder:
    def __init__(self) -> None:
        self._response_text = ""
        self._thread_id = ""
        self._steps = 0
        self._tool_calls: list[ToolCallRecord] = []

    def set_response(self, text: str) -> None:
        self._response_text = text

    def set_thread_id(self, tid: str) -> None:
        self._thread_id = tid

    def increment_steps(self) -> None:
        self._steps += 1

    def add_tool_call(self, name: str, result: StructuredValue | None) -> None:
        self._tool_calls.append(ToolCallRecord(name=name, result=result))

    def add_tool_call_record(self, record: ToolCallRecord) -> None:
        self._tool_calls.append(record)

    def build(self) -> TurnResult:
        return TurnResult(
            response_text=self._response_text,
            thread_id=self._thread_id,
            steps=self._steps,
            tool_calls=self._tool_calls,
        )
