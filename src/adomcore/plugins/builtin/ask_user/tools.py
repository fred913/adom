"""Builtin AskUser plugin tools."""

from __future__ import annotations

import questionary

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("ask_user")


def _ask_user(question: str) -> dict[str, str]:
    answer = questionary.text(question).ask()
    return {"question": question, "answer": answer or ""}


def ask_user_function_bindings() -> list[FunctionBinding]:
    return [
        FunctionBinding(
            spec=FunctionSpec(
                name="ask_user",
                description="Ask the local console user a question and return the answer.",
                input_schema={
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_ask_user,
        )
    ]
