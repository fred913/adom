# adomcore Programmatic Usage Guide

> How to use adomcore as a Python library to build AI agents entirely in code — no `config.yaml` required.

adomcore is a single-instance agent runtime with file-based persistence, a plugin system, MCP integration, streaming, cron scheduling, and automatic context compaction. This document shows how to drive every feature from pure Python, replacing frameworks like LangChain, CrewAI, AutoGen, or the OpenAI Agents SDK.

---

## Table of Contents

- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Quick Start: Minimal Agent in 30 Lines](#quick-start-minimal-agent-in-30-lines)
- [Building the Container from Code](#building-the-container-from-code)
- [Defining Models Programmatically](#defining-models-programmatically)
- [The Plugin System](#the-plugin-system)
  - [BasePlugin](#baseplugin)
  - [Registering Tools (FunctionBinding)](#registering-tools-functionbinding)
  - [System Prompts from Plugins](#system-prompts-from-plugins)
  - [Skills from Plugins](#skills-from-plugins)
  - [Plugin Context: LLM Access Inside Plugins](#plugin-context-llm-access-inside-plugins)
  - [OpenAPI Plugins](#openapi-plugins)
- [Registering Tools Without Plugins](#registering-tools-without-plugins)
- [Conversations: Blocking and Streaming](#conversations-blocking-and-streaming)
- [Multi-Thread Conversations](#multi-thread-conversations)
- [The Streaming Event Model](#the-streaming-event-model)
- [Custom Engine (Bring Your Own LLM)](#custom-engine-bring-your-own-llm)
- [MCP Server Integration](#mcp-server-integration)
- [Cron / Scheduled Tasks](#cron--scheduled-tasks)
- [Context Compaction and Long-Term Memory](#context-compaction-and-long-term-memory)
- [Streaming Tool Progress](#streaming-tool-progress)
- [The Action System (How the Agent Loop Works)](#the-action-system-how-the-agent-loop-works)
- [Domain ID Types](#domain-id-types)
- [Low-Level: Using CapabilityRegistry + ToolExecutor Directly](#low-level-using-capabilityregistry--toolexecutor-directly)
- [Full Example: Replacing LangChain / CrewAI](#full-example-replacing-langchain--crewai)
- [Architecture Reference](#architecture-reference)

---

## Installation

```bash
pip install adomcore
# or with uv
uv add adomcore
```

Requires Python 3.14+.

---

## Core Concepts

| Concept | Class | Role |
|---|---|---|
| **Container** | `AppContainer` | Holds all services, stores, and runtime objects. The root of everything. |
| **Settings** | `AppSettings` | All configuration as a Pydantic model. Defaults work out of the box. |
| **Runtime** | `AgentRuntime` | The agent brain. Runs the decide→act→observe loop. |
| **Engine** | `AgentEngine` (protocol) | Abstraction over the LLM. Ships with `AtomicAgentsEngine` for OpenAI-compatible and Anthropic APIs. |
| **Plugin** | `BasePlugin` | Unit of capability: contributes tools, skills, and system prompts. |
| **CapabilityRegistry** | `CapabilityRegistry` | In-memory store of all callable functions exposed to the agent. |
| **ToolExecutor** | `ToolExecutor` | Executes tool calls by name, supports sync/async/streaming handlers. |
| **ConversationService** | `ConversationService` | High-level entry point: `chat()` and `chat_stream()`. |
| **Thread** | `ThreadId` | An isolated conversation history. Default is `"main"`. |

---

## Quick Start: Minimal Agent in 30 Lines

```python
import asyncio
import tempfile
from pathlib import Path

from adomcore.app.lifespan import build_container, startup, shutdown
from adomcore.app.settings import AppSettings
from adomcore.domain.models import ModelProviderKind

settings = AppSettings(
    default_model_id="main",
    models=[{
        "id": "main",
        "provider": "openai_compatible",
        "model": "gpt-4o-mini",
        "api_base": "https://api.openai.com/v1",
        "api_key": "sk-...",
        "context_window": 128000,
    }],
    storage={"root_dir": tempfile.mkdtemp()},
)

async def main():
    container = await build_container(settings)
    await startup(container)

    result = await container.conversation_service.chat("What is 2 + 2?")
    print(result.response_text)

    await shutdown(container)

asyncio.run(main())
```

That's it. No config file. No YAML. No server. Pure Python.

---

## Building the Container from Code

`build_container(settings)` is the factory that wires everything together. You provide an `AppSettings` instance — constructed however you like — and get back a fully-wired `AppContainer`.

```python
from adomcore.app.settings import AppSettings, RuntimeSettings, StorageSettings
from adomcore.app.lifespan import build_container, startup, shutdown

settings = AppSettings(
    timezone="UTC",
    default_thread_id="main",
    default_model_id="my_model",
    runtime=RuntimeSettings(
        max_loop_steps=12,       # max tool-call loops per turn
        auto_compact=True,        # auto-compact context when it grows too large
        compact_soft_ratio=0.75,  # start compacting at 75% of context window
        compact_hard_ratio=0.9,   # hard limit
        recent_messages_window=24,# how many recent messages to keep in context
    ),
    storage=StorageSettings(root_dir="/tmp/my-agent-data"),
    models=[
        {
            "id": "my_model",
            "provider": "openai_compatible",
            "model": "qwen3",
            "api_base": "http://localhost:11434/v1",
            "context_window": 32000,
        }
    ],
)

container = await build_container(settings)
await startup(container)
```

### AppSettings Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `timezone` | `str` | `"Asia/Shanghai"` | Timezone for cron scheduling |
| `default_thread_id` | `str` | `"main"` | Default conversation thread |
| `default_model_id` | `str` | `"main"` | Which model entry to use |
| `runtime` | `RuntimeSettings` | see above | Runtime tuning |
| `storage` | `StorageSettings` | `{"root_dir": "./data"}` | Where state files go |
| `scheduler` | `SchedulerSettings` | APScheduler, 1s tick | Cron backend config |
| `plugins` | `PluginSettings` | empty | Plugin dirs and per-plugin config |
| `models` | `list[dict]` | `[]` | Model definitions |
| `api` | `ApiSettings` | `0.0.0.0:8000` | Only relevant when running the HTTP server |

---

## Defining Models Programmatically

Each model entry in `settings.models` is a dict that maps to `ModelSpec`:

```python
# OpenAI-compatible (works with OpenAI, Ollama, LM Studio, vLLM, Groq, Together, etc.)
{
    "id": "local_llama",
    "provider": "openai_compatible",
    "model": "llama3.1",
    "api_base": "http://localhost:11434/v1",
    "api_key": None,  # not needed for local
    "context_window": 128000,
    "supports_tools": True,
    "supports_streaming": True,
    "extra_config": {},  # passed directly to the API call kwargs
}

# Anthropic Claude
{
    "id": "claude",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key": "sk-ant-...",
    "context_window": 200000,
    "token_estimate_provider": "anthropic_count_tokens",
}
```

### ModelSpec Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | required | Unique identifier |
| `provider` | `"openai_compatible"` or `"anthropic"` | required | Which client to use |
| `model` | `str` | required | Model name sent to API |
| `context_window` | `int` | required | Context window size in tokens |
| `api_base` | `str \| None` | `None` | API endpoint URL |
| `api_key` | `str \| None` | `None` | API key |
| `supports_tools` | `bool` | `True` | Whether model supports function calling |
| `supports_streaming` | `bool` | `True` | Whether model supports streaming |
| `extra_config` | `dict` | `{}` | Extra kwargs passed to API calls (e.g. `temperature`, `top_p`) |
| `token_estimate_provider` | `str` | `"heuristic"` | `"heuristic"`, `"tiktoken"`, or `"anthropic_count_tokens"` |

---

## The Plugin System

Plugins are the primary way to give the agent capabilities. A plugin contributes any combination of:

- **Tools** (functions the agent can call)
- **Skills** (instructions injected into the system prompt)
- **System prompt fragments** (with optional priority ordering)

### BasePlugin

```python
from adomcore.plugins.base import BasePlugin
from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.skills import SkillSpec
from adomcore.domain.ids import PluginId, SkillId

class MyPlugin(BasePlugin):
    plugin_id = "my_plugin"           # unique string identifier
    plugin_name = "My Plugin"          # display name
    plugin_version = "1.0.0"           # semver
    plugin_description = "Does things" # shown to LLM in tool descriptions

    def functions(self) -> list[FunctionBinding]:
        """Return tool definitions + their handler functions."""
        return []

    def skills(self) -> list[SkillSpec]:
        """Return skill instructions injected into system prompt."""
        return []

    def system_prompt(self) -> str | tuple[str, int | float]:
        """Return a system prompt fragment. Optionally (text, priority)."""
        return ""
```

### Registering Tools (FunctionBinding)

Each tool is a `FunctionBinding` pairing a `FunctionSpec` (JSON Schema metadata) with a callable handler.

```python
from pydantic import BaseModel

class SearchArgs(BaseModel):
    query: str
    max_results: int = 5

async def web_search(query: str, max_results: int = 5) -> dict:
    # your implementation
    return {"results": [...]}

class SearchPlugin(BasePlugin):
    plugin_id = "search"
    plugin_name = "Web Search"
    plugin_description = "Search the web."

    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="web_search",
                    description="Search the web for information.",
                    input_schema=SearchArgs.model_json_schema(),
                    source_plugin=self.id,
                ),
                handler=web_search,
            )
        ]
```

**Handler rules:**
- Can be a regular function, an `async` function, a generator, or an async generator
- Arguments are passed as `**kwargs` matching the `input_schema` properties
- Return value is serialized and sent back to the LLM as a tool result
- Sync functions are automatically run in a thread pool via `asyncio.to_thread()`

**Using Pydantic for schemas:**
Use `MyArgsModel.model_json_schema()` to auto-generate the JSON Schema from a Pydantic model. This is the recommended approach.

### System Prompts from Plugins

```python
class MyPlugin(BasePlugin):
    plugin_id = "my_plugin"
    plugin_name = "My Plugin"

    def system_prompt(self) -> str:
        return "Always respond in JSON format."

    # Or with priority (higher = earlier in prompt):
    def system_prompt(self) -> tuple[str, int]:
        return ("Always respond in JSON format.", 100)
```

All plugin system prompts are concatenated into the final system prompt, sorted by priority (highest first). Default priority is 0.

### Skills from Plugins

Skills are named instructions that appear in a `## Skills` section of the system prompt:

```python
from adomcore.domain.skills import SkillSpec
from adomcore.domain.ids import SkillId

class MyPlugin(BasePlugin):
    plugin_id = "my_plugin"
    plugin_name = "My Plugin"

    def skills(self) -> list[SkillSpec]:
        return [
            SkillSpec(
                id=SkillId("code_review"),
                name="Code Review",
                content="When reviewing code, check for security issues, "
                        "performance problems, and style violations.",
            ),
            SkillSpec(
                id=SkillId("sql_expert"),
                name="SQL Expert",
                content="Write efficient SQL. Prefer CTEs over subqueries.",
            ),
        ]
```

### Plugin Context: LLM Access Inside Plugins

When a plugin needs to call the LLM itself (e.g., to summarize, classify, or generate structured data inside a tool handler), it can access the model through `PluginContext`:

```python
from adomcore.plugins.base import BasePlugin
from adomcore.plugins.context import PluginContext

class SmartPlugin(BasePlugin):
    plugin_id = "smart"
    plugin_name = "Smart Plugin"

    def bind_context(self, context: PluginContext) -> "SmartPlugin":
        self._context = context
        return self

    def functions(self) -> list[FunctionBinding]:
        async def summarize(text: str) -> dict:
            model = self._context.get_model()  # gets default model handle
            summary = await model.generate_text(
                f"Summarize this:\n{text}",
                system="You are a concise summarizer.",
            )
            return {"summary": summary}

        # Or for structured output:
        async def classify(text: str) -> dict:
            model = self._context.get_model()
            result = await model.generate_structured(
                f"Classify this text:\n{text}",
                system="Return JSON with a 'category' field.",
            )
            return result

        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="summarize",
                    description="Summarize text using the LLM.",
                    input_schema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                    source_plugin=self.id,
                ),
                handler=summarize,
            ),
        ]
```

`PluginModelHandle` provides:
- `generate_text(prompt, *, system=None) -> str`
- `generate_structured(prompt, *, system=None) -> dict` (asks the model to return JSON)

You can also use `self._context.get_model("other_model_id")` to target a specific model.

### OpenAPI Plugins

Wrap any OpenAPI spec as agent-callable tools with zero boilerplate:

```python
from adomcore.plugins.openapi import OpenApiPlugin

github_plugin = OpenApiPlugin(
    plugin_id="github_api",
    name="GitHub API",
    description="Interact with GitHub.",
    base_url="https://api.github.com",
    auth_headers={"Authorization": "Bearer ghp_..."},
    spec={
        "openapi": "3.0.0",
        "paths": {
            "/repos/{owner}/{repo}": {
                "get": {
                    "operationId": "getRepo",
                    "summary": "Get repository info",
                    "parameters": [
                        {"name": "owner", "in": "path", "required": True,
                         "schema": {"type": "string"}},
                        {"name": "repo", "in": "path", "required": True,
                         "schema": {"type": "string"}},
                    ],
                }
            },
            "/repos/{owner}/{repo}/issues": {
                "post": {
                    "operationId": "createIssue",
                    "summary": "Create an issue",
                    "parameters": [
                        {"name": "owner", "in": "path", "required": True,
                         "schema": {"type": "string"}},
                        {"name": "repo", "in": "path", "required": True,
                         "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "body": {"type": "string"},
                                    },
                                    "required": ["title"],
                                }
                            }
                        },
                    },
                }
            },
        },
    },
)
```

Each OpenAPI operation becomes a tool. Path parameters, query parameters, and request bodies are automatically extracted from the spec.

---

## Registering Tools Without Plugins

For quick prototyping, register tools directly on the `CapabilityRegistry`:

```python
from adomcore.domain.capabilities import FunctionSpec

def get_weather(city: str) -> dict:
    return {"city": city, "temp": 22, "condition": "sunny"}

container.capability_registry.register(
    FunctionSpec(
        name="get_weather",
        description="Get current weather for a city.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    ),
    get_weather,
)
```

Or register a dynamic provider (re-evaluated on every turn):

```python
def my_dynamic_tools() -> list[FunctionBinding]:
    # can return different tools based on runtime state
    return [...]

container.capability_registry.register_provider("my_tools", my_dynamic_tools)
```

---

## Conversations: Blocking and Streaming

### Blocking

```python
result = await container.conversation_service.chat("Explain quantum computing")
print(result.response_text)  # the final assistant message
print(result.steps)          # how many LLM calls were made
print(result.tool_calls)     # list of tool calls made during the turn
```

### Streaming

```python
from adomcore.domain.streaming import TurnStreamEventType

async for event in container.conversation_service.chat_stream("Tell me a joke"):
    match event.event:
        case TurnStreamEventType.ASSISTANT_TEXT_DELTA:
            print(event.data["text"], end="", flush=True)
        case TurnStreamEventType.TOOL_CALL_STARTED:
            print(f"\n[Calling {event.data['tool_name']}]")
        case TurnStreamEventType.TOOL_RESULT:
            print(f"\n[Tool result: {event.data['result']}]")
        case TurnStreamEventType.ASSISTANT_TEXT_DONE:
            print()  # newline after final text
```

---

## Multi-Thread Conversations

Threads are isolated conversation histories. Use them for parallel conversations, user sessions, or sub-tasks:

```python
from adomcore.domain.ids import ThreadId

# Each thread has its own history and memory
result1 = await container.conversation_service.chat(
    "You are a Python expert.", thread_id=ThreadId("python_chat")
)
result2 = await container.conversation_service.chat(
    "You are a Rust expert.", thread_id=ThreadId("rust_chat")
)

# Continue each independently
await container.conversation_service.chat(
    "How do I read a file?", thread_id=ThreadId("python_chat")
)
await container.conversation_service.chat(
    "How do I read a file?", thread_id=ThreadId("rust_chat")
)
```

---

## The Streaming Event Model

| Event | `data` Keys | Description |
|---|---|---|
| `ASSISTANT_TEXT_DELTA` | `text`, `thread_id` | Incremental text token from the LLM |
| `TOOL_CALL_STARTED` | `call_id`, `tool_name`, `thread_id` | A new tool call began |
| `TOOL_CALL_DELTA` | `call_id`, `tool_name`, `arguments_delta`, `thread_id` | Streaming tool call arguments |
| `TOOL_CALL_FINISHED` | `call_id`, `tool_name`, `arguments`, `thread_id` | Tool call arguments fully received |
| `TOOL_PROGRESS` | `call_id`, `tool_name`, `payload`, `thread_id` | Interim progress from a long-running tool |
| `TOOL_PROGRESS_SUMMARY` | `call_id`, `tool_name`, `text`, `thread_id` | LLM-generated summary of tool progress |
| `TOOL_RESULT` | `name`, `call_id`, `result`, `is_error`, `thread_id` | Final tool result |
| `ASSISTANT_TEXT_DONE` | `text`, `thread_id` | Full assistant response text |
| `TURN_DONE` | `thread_id`, `steps`, `tool_calls` | Turn complete |

---

## Custom Engine (Bring Your Own LLM)

The `AgentEngine` protocol has three methods. Implement them to plug in any LLM:

```python
from collections.abc import AsyncIterator
from typing import Any

from adomcore.domain.actions import AgentDecision, CallFunctionAction, RespondAction
from adomcore.domain.streaming import EngineDecisionEvent, EngineEvent

class MyCustomEngine:
    """Implements the AgentEngine protocol."""

    async def decide(self, context: dict[str, Any]) -> AgentDecision:
        """
        Given context with keys:
          - "system": str (system prompt)
          - "messages": list[dict] (conversation history)
          - "tools": list[dict] (available tool specs)
        Return an AgentDecision with a list of actions.
        """
        # Example: always respond with text
        return AgentDecision(actions=[
            RespondAction(text="Hello from custom engine!")
        ])

        # Or call a tool:
        return AgentDecision(actions=[
            CallFunctionAction(
                function_name="web_search",
                arguments={"query": "latest news"},
                call_id="call_001",
            )
        ])

    async def stream_decide(
        self, context: dict[str, Any]
    ) -> AsyncIterator[EngineEvent]:
        """Streaming version of decide(). Yield events, end with EngineDecisionEvent."""
        decision = await self.decide(context)
        yield EngineDecisionEvent(kind="decision", decision=decision)

    async def summarise(self, prompt: str) -> dict[str, Any]:
        """Used for context compaction. Return JSON with 'summary' key."""
        return {"summary": "A summary of the conversation so far."}
```

Inject it into the container:

```python
container.engine = MyCustomEngine()
# Rebuild the runtime with the new engine
from adomcore.runtime.agent_runtime import AgentRuntime
container.agent_runtime = AgentRuntime(
    container.agent_service,
    container.thread_store,
    container.context_builder,
    container.action_router,
    container.compact_manager,
    container.engine,
    max_loop_steps=12,
)
container.conversation_service = ConversationService(container.agent_runtime)
```

---

## MCP Server Integration

Connect MCP (Model Context Protocol) tool servers programmatically:

```python
from adomcore.domain.mcp import McpServerSpec
from adomcore.domain.ids import McpServerId
from adomcore.integrations.mcp.stdio_client import StdioMcpClient

# Define the MCP server
spec = McpServerSpec(
    id=McpServerId("filesystem"),
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    env={},
)

# Start the MCP client
client = StdioMcpClient(spec)
await client.start()

# Discover tools
tools = await client.list_tools()
for tool in tools:
    print(f"  {tool.name}: {tool.description}")

# Call a tool directly
result = await client.call_tool("read_file", {"path": "/tmp/test.txt"})

# Or register it with the session manager for use by the agent
await container.mcp_session_manager.connect(spec)
```

The `ActionRouter` automatically routes `CallMcpToolAction` to the right MCP session. The agent can also self-register MCP servers at runtime via self-mutation actions.

---

## Cron / Scheduled Tasks

Schedule recurring agent actions:

```python
from adomcore.domain.cron import CronTriggerSpec, ScheduledInstruction
from adomcore.domain.ids import CronJobId, ThreadId
from datetime import datetime, UTC

job = ScheduledInstruction(
    job_id=CronJobId("daily_summary"),
    trigger=CronTriggerSpec(cron_expr="0 9 * * *"),  # 9 AM daily
    instruction_text="Summarize yesterday's activity and email the report.",
    target_thread_id=ThreadId("main"),
    enabled=True,
    created_at=datetime.now(UTC),
)

await container.scheduler_service.add_job(job)
await container.scheduler_service.start()  # already called by startup()
```

When the cron fires, `CronDispatchService` calls `agent_runtime.run_timer_turn()` which injects the instruction as a system event and runs the agent loop.

---

## Context Compaction and Long-Term Memory

adomcore automatically compacts conversation context when it approaches the model's context window:

- **Soft ratio** (default 0.75): triggers compaction using the LLM `summarise()` method
- **Hard ratio** (default 0.9): forceful compaction
- Compaction produces a `CompactSnapshot` containing: summary, facts, preferences, tasks, and important decisions
- The snapshot is injected into the system prompt as long-term memory on subsequent turns

The `CompactSnapshot` model:

```python
class CompactSnapshot:
    thread_id: ThreadId
    summary: str                        # narrative summary
    facts: list[MemoryFact]             # extracted facts
    preferences: list[MemoryPreference] # user preferences
    tasks: list[MemoryTask]             # tracked tasks
    important_decisions: list[str]
    recent_capability_changes: list[str]
    compacted_at: datetime | None
    covers_up_to_event_id: str | None
```

---

## Streaming Tool Progress

For long-running tools, yield progress events so the user sees real-time updates:

```python
from adomcore.services.tool_executor import ToolProgressUpdate, ToolFinalUpdate

async def long_running_analysis(data: str):
    """Async generator tool that streams progress."""
    yield ToolProgressUpdate(kind="progress", payload={"step": "parsing", "pct": 10})
    parsed = parse(data)

    yield ToolProgressUpdate(kind="progress", payload={"step": "analyzing", "pct": 50})
    result = analyze(parsed)

    yield ToolProgressUpdate(kind="progress", payload={"step": "formatting", "pct": 90})
    formatted = format_result(result)

    # MUST yield a final result
    yield ToolFinalUpdate(kind="final", result={"analysis": formatted})
```

You can also yield plain dicts:

```python
async def my_tool(query: str):
    yield {"kind": "progress", "payload": {"message": "Searching..."}}
    results = await search(query)
    yield {"kind": "final", "result": {"results": results}}
```

Or yield strings for simple progress messages:

```python
async def my_tool(query: str):
    yield "Searching..."          # becomes ToolProgressUpdate(payload={"message": "..."})
    results = await search(query)
    yield ToolFinalUpdate(kind="final", result=results)
```

The runtime automatically asks the LLM to summarize progress events and injects summaries into the conversation context as `assistant_progress` messages.

---

## The Action System (How the Agent Loop Works)

Each agent turn runs a loop (up to `max_loop_steps`):

1. **Build context** — system prompt + conversation history + tool specs
2. **Engine decides** — LLM returns `AgentDecision(actions=[...])`
3. **Route actions** — `ActionRouter` dispatches each action:
   - `RespondAction` → final text response (breaks the loop)
   - `CallFunctionAction` → local tool execution
   - `CallMcpToolAction` → MCP server tool call
   - `SwitchModelAction` → change active model
   - `AddSkillAction` / `EnableSkillAction` / `DisableSkillAction` → skill mutation
   - `AddMcpServerAction` / `EnableMcpServerAction` / `DisableMcpServerAction` → MCP mutation
   - `CreateCronJobAction` / `RemoveCronJobAction` → schedule management
   - `InstallPluginAction` / `EnablePluginAction` / `DisablePluginAction` → plugin mutation
4. **Append results to thread** → tool results become context for next loop iteration
5. **Repeat** until a `RespondAction` is produced or max steps reached

All actions are frozen dataclasses in `adomcore.domain.actions`.

---

## Domain ID Types

All IDs are `NewType` wrappers over `str` for type safety:

```python
from adomcore.domain.ids import (
    ThreadId,      # conversation thread
    PluginId,      # plugin identifier
    SkillId,       # skill identifier
    McpServerId,   # MCP server identifier
    CronJobId,     # cron job identifier
)
```

---

## Low-Level: Using CapabilityRegistry + ToolExecutor Directly

For testing or embedding tool execution without the full agent:

```python
import asyncio
from adomcore.domain.capabilities import FunctionSpec
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.tool_executor import ToolExecutor

registry = CapabilityRegistry()

registry.register(
    FunctionSpec(
        name="multiply",
        description="Multiply two numbers.",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    ),
    lambda a, b: {"result": a * b},
)

executor = ToolExecutor(registry)
print(asyncio.run(executor.execute("multiply", {"a": 6, "b": 7})))
# {"result": 42}
```

---

## Full Example: Replacing LangChain / CrewAI

Here is a complete, self-contained agent with web search, file operations, and code execution — no config file, no server:

```python
import asyncio
import subprocess
import tempfile
from pathlib import Path

from adomcore.app.lifespan import build_container, startup, shutdown
from adomcore.app.settings import AppSettings
from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import SkillId
from adomcore.domain.skills import SkillSpec
from adomcore.domain.streaming import TurnStreamEventType
from adomcore.plugins.base import BasePlugin


# ── Tool implementations ────────────────────────────────────────

async def run_python(code: str) -> dict:
    """Execute Python code in a subprocess."""
    result = subprocess.run(
        ["python", "-c", code],
        capture_output=True, text=True, timeout=30,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def read_file(path: str) -> dict:
    return {"content": Path(path).read_text()}


def write_file(path: str, content: str) -> dict:
    Path(path).write_text(content)
    return {"status": "written", "path": path}


def list_directory(path: str = ".") -> dict:
    import os
    return {"entries": os.listdir(path)}


# ── Plugin definition ───────────────────────────────────────────

class DevAssistantPlugin(BasePlugin):
    plugin_id = "dev_assistant"
    plugin_name = "Dev Assistant"
    plugin_description = "Code execution and filesystem tools."

    def functions(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="run_python",
                    description="Execute Python code and return stdout/stderr.",
                    input_schema={
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                    source_plugin=self.id,
                ),
                handler=run_python,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="read_file",
                    description="Read a text file.",
                    input_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                    source_plugin=self.id,
                ),
                handler=read_file,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="write_file",
                    description="Write content to a file.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                    source_plugin=self.id,
                ),
                handler=write_file,
            ),
            FunctionBinding(
                spec=FunctionSpec(
                    name="list_directory",
                    description="List files in a directory.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "."},
                        },
                    },
                    source_plugin=self.id,
                ),
                handler=list_directory,
            ),
        ]

    def skills(self) -> list[SkillSpec]:
        return [
            SkillSpec(
                id=SkillId("coding_best_practices"),
                name="Coding Best Practices",
                content="Write clean, tested code. Use type hints. "
                        "Handle errors gracefully. Prefer standard library.",
            ),
        ]

    def system_prompt(self) -> tuple[str, int]:
        return (
            "You are a senior software engineer assistant. "
            "Use the available tools to help with coding tasks. "
            "Always test code by running it before presenting results.",
            10,  # priority
        )


# ── Main ────────────────────────────────────────────────────────

async def main():
    settings = AppSettings(
        default_model_id="main",
        models=[{
            "id": "main",
            "provider": "openai_compatible",
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            "api_key": "sk-...",
            "context_window": 128000,
        }],
        storage={"root_dir": tempfile.mkdtemp()},
    )

    container = await build_container(settings)
    container.plugin_manager.activate_instance(DevAssistantPlugin())
    await startup(container)

    try:
        # Multi-turn streaming conversation
        prompts = [
            "Write a Python function that finds prime numbers up to N, "
            "save it to /tmp/primes.py, then run it with N=100.",
            "Now add unit tests and run them.",
        ]
        for prompt in prompts:
            print(f"\n{'='*60}\nUser: {prompt}\n{'='*60}")
            async for event in container.conversation_service.chat_stream(prompt):
                match event.event:
                    case TurnStreamEventType.ASSISTANT_TEXT_DELTA:
                        print(event.data["text"], end="", flush=True)
                    case TurnStreamEventType.TOOL_CALL_STARTED:
                        print(f"\n  > Calling {event.data['tool_name']}...")
                    case TurnStreamEventType.TOOL_RESULT:
                        r = event.data.get("result", "")
                        preview = str(r)[:200]
                        print(f"  > Result: {preview}")
                    case TurnStreamEventType.ASSISTANT_TEXT_DONE:
                        print()
    finally:
        await shutdown(container)


if __name__ == "__main__":
    asyncio.run(main())
```

### What this replaces from other frameworks

| Other Framework Concept | adomcore Equivalent |
|---|---|
| LangChain `Tool` / `@tool` decorator | `FunctionBinding` + `FunctionSpec` |
| LangChain `AgentExecutor` | `AgentRuntime` (decide→act→observe loop) |
| LangChain `ChatPromptTemplate` | Plugin `system_prompt()` + `ContextBuilder` |
| LangChain `Memory` / `ConversationBufferMemory` | Thread store + automatic compaction |
| CrewAI `Agent` with role/goal/backstory | `BasePlugin` with `system_prompt()` + `skills()` |
| CrewAI `Task` / `Crew` | Multiple plugins + `ConversationService.chat()` |
| AutoGen `AssistantAgent` + `UserProxyAgent` | `ConversationService` + tool plugins |
| OpenAI Agents SDK `Agent` | `AppContainer` + plugins + engine |
| OpenAI Agents SDK `Runner.run()` | `conversation_service.chat()` or `chat_stream()` |
| All frameworks: "chains" / "graphs" / "workflows" | Sequential `chat()` calls on different threads |

### Key advantages of adomcore

1. **Single file, zero config** — construct `AppSettings` in Python and go
2. **Real streaming** — token-level streaming with tool progress events
3. **Automatic context management** — compaction, summarization, long-term memory built in
4. **Plugin-as-capability** — tools + skills + system prompts in one cohesive unit
5. **MCP native** — first-class MCP server integration
6. **File-based persistence** — no database, works anywhere, trivially inspectable
7. **Self-mutation** — the agent can add/remove its own tools, skills, and MCP servers at runtime
8. **Cron scheduling** — built-in recurring task execution
9. **Multi-model** — define multiple models and switch between them per-request or via agent action
10. **Protocol-based engine** — swap the LLM backend without touching anything else

---

## Architecture Reference

```
AppSettings ──► build_container() ──► AppContainer
                                          │
                 ┌────────────────────────┼────────────────────────┐
                 │                        │                        │
           PluginManager          AgentRuntime              SchedulerService
           ├─ BasePlugin          ├─ ContextBuilder         ├─ CronDispatchService
           ├─ CapabilityRegistry  ├─ ActionRouter           └─ APSchedulerBackend
           └─ PluginContext       ├─ CompactManager
                                  └─ AgentEngine
                                       │
                              AtomicAgentsEngine
                              ├─ OpenAI client
                              └─ Anthropic client

ConversationService ──► AgentRuntime.run_user_turn[_stream]()
                              │
                         ┌────┴────┐
                     ContextBuilder  ActionRouter
                     (build prompt)  (dispatch actions)
                         │               │
                    ThreadStore    ┌──────┼──────┐
                    CompactStore   │      │      │
                    SkillService   Tool   MCP    Self-
                    ModelService   Exec   Sess   Mutation
```
