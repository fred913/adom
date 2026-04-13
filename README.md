# adomcore

A single-instance AI agent runtime. No database. File-based persistence only.

## How it works

- `config.yaml` — all configuration (models, API keys, plugins, scheduler)
- `data/` — runtime state (JSON5 snapshots + JSONL event streams)
- `logs/` — timestamped log files

One process. One agent. One `AgentRuntime` owns all control flow.

---

## Setup

**1. Install uv** (if you don't have it)

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

**2. Clone and enter the project**

```bash
git clone <repo-url>
cd adom
```

**3. Copy the sample config**

```bash
cp config.sample.yaml config.yaml
```

**4. Edit `config.yaml`** — set the model and API key you want to use:

```yaml
default_model_id: main

models:
  - id: main
    provider: openai_compatible
    api_base: http://localhost:11434/v1   # Ollama, LM Studio, etc.
    model: qwen3
    api_key: null                         # not needed for local models
    enabled: true
```

For Anthropic Claude, set `api_key` and `enabled: true` on the `claude_main` entry.

**5. Install dependencies**

```bash
uv sync
```

**6. Start the server**

```bash
uv run adomcore serve
```

Server starts at `http://localhost:8000`.

---

## Quick test

```bash
# Health check
curl http://localhost:8000/health

# Send a message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, what can you do?"}'

# Check agent state
curl http://localhost:8000/agent/state

# List available models
curl http://localhost:8000/models
```

### Streaming chat

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Use a tool if needed, and stream everything."}'
```

The stream is sent as SSE with structured events such as:

- `assistant_text_delta`
- `tool_call_started`
- `tool_call_delta`
- `tool_call_finished`
- `tool_result`
- `assistant_text_done`
- `turn_done`

Plugins can now also register persistent **skills** and **MCP servers** during
setup, in addition to regular functions/tools. Async plugin setup is supported,
so a plugin can `await ctx.register_skill(...)` or `await ctx.register_mcp_server(...)`.

---

## Run the demo (no server needed)

```bash
uv run python demo.py
```

Runs a minimal streamed chat with an in-memory plugin that:

- registers 3 tools
- registers a skill during plugin setup
- uses Pydantic `BaseModel.model_json_schema()` for tool schemas
- prints streamed runtime events to stdout

More examples in `examples/plugins/`:

```bash
uv run python examples/plugins/calculator.py
uv run python examples/plugins/multi_tool.py
```

There is also a reusable OpenAPI plugin helper in `src/adomcore/plugins/openapi.py`
plus an example module in `examples/plugins/openapi_petstore.py`. The intended
pattern is to instantiate `OpenApiPlugin(...)` from your own plugin module and
point it at the OpenAPI spec/base URL you want to expose as agent-callable tools.
Plugin instances now carry their own runtime metadata (`id`, `name`, `description`,
etc.), so the loaded plugin object itself is the single source of truth.

Built-in plugins also include `opencode`, which can call an `opencode serve`
instance over HTTP. On first use it will try `GET /global/health`, start
`opencode serve` if needed, create a session, and submit the delegated task.
Later calls reuse the same live session automatically. Configure it under
`plugins.config.opencode` in `config.yaml` if you need a custom command, host,
port, auth, or startup timeout.

---

## Tests

```bash
uv run pytest
```

Coverage run:

```bash
uv run --with pytest-cov pytest --cov=adomcore --cov-report=term-missing
```

---

## Project layout

```
config.sample.yaml   # copy this to config.yaml
config.yaml          # your local config (gitignored)
data/                # runtime state (gitignored)
logs/                # log files (gitignored)
src/adomcore/
  app/               # FastAPI app, settings, lifespan
  api/               # HTTP routers and schemas
  domain/            # pure dataclasses, no I/O
  runtime/           # AgentRuntime — the single brain
  services/          # business logic
  storage/           # file stores (JSON5, JSONL, YAML)
  integrations/      # LLM clients, scheduler, MCP
  plugins/           # plugin protocol + builtin plugins
demo.py
examples/
```

---

## Persistence rules

| Format | Used for |
|--------|----------|
| YAML   | Static config (`config.yaml`) |
| JSON5  | Current state snapshots (`data/**/*.json5`) |
| JSONL  | Append-only event streams (`data/**/*.jsonl`) |
