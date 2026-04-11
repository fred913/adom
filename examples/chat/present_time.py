"""Minimal streamed chat demo using the real configured model from config.yaml."""

import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from adomcore.app.lifespan import build_container, shutdown, startup
from adomcore.app.settings import AppSettings
from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.streaming import TurnStreamEventType
from adomcore.plugins.context import PluginContext


class AddArgs(BaseModel):
    a: int
    b: int


class EchoArgs(BaseModel):
    text: str


class FormatTimeArgs(BaseModel):
    timezone_label: str = "UTC"


def add_numbers(a: int, b: int) -> dict[str, int]:
    return {"sum": a + b}


def echo_text(text: str) -> dict[str, str]:
    return {"echo": text}


def format_time(timezone_label: str = "UTC") -> dict[str, str]:
    return {
        "time": datetime.now(UTC).isoformat(),
        "timezone": timezone_label,
    }


class DemoPlugin:
    async def setup(self, ctx: PluginContext) -> None:
        await ctx.register_skill(
            skill_id="demo_tool_preference",
            name="Demo tool preference",
            content="Use the available demo tools for math, echo, and time questions.",
        )
        ctx.register_function(
            FunctionSpec(
                name="add_numbers",
                description="Add two integers.",
                input_schema=AddArgs.model_json_schema(),
            ),
            add_numbers,
        )
        ctx.register_function(
            FunctionSpec(
                name="echo_text",
                description="Echo text back to the caller.",
                input_schema=EchoArgs.model_json_schema(),
            ),
            echo_text,
        )
        ctx.register_function(
            FunctionSpec(
                name="format_time",
                description="Return the current UTC time.",
                input_schema=FormatTimeArgs.model_json_schema(),
            ),
            format_time,
        )


def _load_demo_settings(temp_root: Path) -> AppSettings:
    config_path = Path.cwd() / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            "config.yaml not found. Copy config.sample.yaml to config.yaml and set a working model first."
        )
    settings = AppSettings.load(config_path)
    return settings.model_copy(
        update={
            "storage": settings.storage.model_copy(update={"root_dir": str(temp_root)}),
        }
    )


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="adomcore-demo-") as tmp:
        data_dir = Path(tmp)
        settings = _load_demo_settings(data_dir)
        container = await build_container(settings)

        plugin_ctx = PluginContext(
            container.capability_registry,
            container.self_mutation_service,
        )
        await DemoPlugin().setup(plugin_ctx)

        await startup(container)
        try:
            prompt = sys.argv[1] if len(sys.argv) > 1 else "What time is it right now?"
            is_in_middle_of_line = False
            print("Streaming chat with the real configured model from config.yaml...")
            print(f"Prompt: {prompt}")
            async for event in container.conversation_service.chat_stream(prompt):
                match event.event:
                    case TurnStreamEventType.ASSISTANT_TEXT_DELTA:
                        text = str(event.data.get("text", ""))
                        if not is_in_middle_of_line:
                            print("Adom: ", end="", flush=True)
                            is_in_middle_of_line = True
                        print(text, end="", flush=True)
                    case TurnStreamEventType.TOOL_CALL_STARTED:
                        if is_in_middle_of_line:
                            print()
                            is_in_middle_of_line = False
                        function_name = str(event.data.get("tool_name", ""))
                        print(f"Adom calls {function_name}: ", end="", flush=True)
                        is_in_middle_of_line = True
                    case TurnStreamEventType.TOOL_CALL_DELTA:
                        print(
                            str(event.data.get("arguments_delta", "")),
                            end="",
                            flush=True,
                        )
                    case TurnStreamEventType.TOOL_RESULT:
                        if is_in_middle_of_line:
                            print()
                            is_in_middle_of_line = False
                        function_name = str(
                            event.data.get("tool_name")
                            or event.data.get("name", "tool")
                        )
                        response = json.dumps(
                            event.data.get("result"), ensure_ascii=False, default=str
                        )
                        print(f"Tool {function_name} responded: {response}")
                    case TurnStreamEventType.ASSISTANT_TEXT_DONE:
                        if is_in_middle_of_line:
                            print()
                            is_in_middle_of_line = False
                    case _:
                        pass
            if is_in_middle_of_line:
                print()
            print(f"Demo data dir: {data_dir}")
        finally:
            await shutdown(container)


if __name__ == "__main__":
    asyncio.run(main())
