"""Multi-turn streamed chat REPL using the real configured model from config.yaml."""

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from adomcore.app.container import AppContainer
from adomcore.app.lifespan import build_container, shutdown, startup
from adomcore.app.settings import AppSettings
from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import SkillId
from adomcore.domain.skills import SkillSpec
from adomcore.domain.streaming import TurnStreamEventType
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.builtin.core_admin.plugin import BuiltinCoreAdminPlugin
from adomcore.plugins.builtin.cron.plugin import BuiltinCronPlugin
from adomcore.plugins.builtin.memory_admin.plugin import BuiltinMemoryAdminPlugin


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


class DemoPlugin(BasePlugin):
    plugin_id = "demo"
    plugin_name = "Demo Plugin"
    plugin_description = "In-memory demo plugin for the chat REPL."

    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="add_numbers",
                    description="Add two integers.",
                    input_schema=AddArgs.model_json_schema(),
                    source_plugin=self.id,
                ),
                handler=add_numbers,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="echo_text",
                    description="Echo text back to the caller.",
                    input_schema=EchoArgs.model_json_schema(),
                    source_plugin=self.id,
                ),
                handler=echo_text,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="format_time",
                    description="Return the current UTC time.",
                    input_schema=FormatTimeArgs.model_json_schema(),
                    source_plugin=self.id,
                ),
                handler=format_time,
            ),
        ]

    def skills(self) -> list[SkillSpec]:
        return [
            SkillSpec(
                id=SkillId("demo_tool_preference"),
                name="Demo tool preference",
                content="Use the available demo tools for math, echo, and time questions.",
            )
        ]

    def system_prompt(self) -> str:
        return "Use demo tools when they help with math, echo, or time requests."


def activate_demo_plugin(container: AppContainer) -> None:
    container.plugin_manager.activate_instance(DemoPlugin())


def activate_repo_plugins(container: AppContainer) -> None:
    container.plugin_manager.activate_instance(BuiltinCronPlugin())
    container.plugin_manager.activate_instance(BuiltinCoreAdminPlugin())
    container.plugin_manager.activate_instance(BuiltinMemoryAdminPlugin())


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


async def _stream_prompt(container: AppContainer, prompt: str) -> None:
    is_in_middle_of_line = False

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
                print(str(event.data.get("arguments_delta", "")), end="", flush=True)
            case TurnStreamEventType.TOOL_RESULT:
                if is_in_middle_of_line:
                    print()
                    is_in_middle_of_line = False
                function_name = str(
                    event.data.get("tool_name") or event.data.get("name", "tool")
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


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="adomcore-repl-") as tmp:
        data_dir = Path(tmp)
        settings = _load_demo_settings(data_dir)
        container = await build_container(settings)
        activate_repo_plugins(container)
        activate_demo_plugin(container)

        await startup(container)
        try:
            print("Multi-turn Adom REPL (Ctrl-C to exit)")
            print(f"Demo data dir: {data_dir}")
            while True:
                prompt = input("You: ").strip()
                if not prompt:
                    continue
                await _stream_prompt(container, prompt)
        except KeyboardInterrupt:
            print("\nExiting.")
        finally:
            await shutdown(container)


if __name__ == "__main__":
    asyncio.run(main())
