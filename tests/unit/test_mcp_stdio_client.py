from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp import types as mcp_types

from adomcore.domain.ids import McpServerId
from adomcore.domain.mcp import McpServerSpec
from adomcore.integrations.mcp import stdio_client as stdio_client_module
from adomcore.integrations.mcp.stdio_client import StdioMcpClient


def _make_spec() -> McpServerSpec:
    return McpServerSpec(
        id=McpServerId("demo"),
        command="python",
        args=["-m", "demo_server"],
        env={"DEMO": "1"},
    )


@pytest.mark.asyncio
async def test_stdio_mcp_client_initializes_and_lists_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    @asynccontextmanager
    async def fake_stdio_client(params: object):
        captured["params"] = params
        try:
            yield ("read_stream", "write_stream")
        finally:
            captured["transport_closed"] = True

    class _FakeSession:
        def __init__(self, read_stream: object, write_stream: object) -> None:
            captured["streams"] = (read_stream, write_stream)

        async def __aenter__(self) -> "_FakeSession":
            captured["session_entered"] = True
            return self

        async def __aexit__(self, *args: object) -> None:
            captured["session_closed"] = True

        async def initialize(self) -> None:
            captured["initialized"] = True

        async def list_tools(self) -> mcp_types.ListToolsResult:
            return mcp_types.ListToolsResult(
                tools=[
                    mcp_types.Tool(
                        name="add",
                        description="Add two numbers",
                        inputSchema={"type": "object"},
                    )
                ]
            )

    monkeypatch.setattr(stdio_client_module, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(stdio_client_module, "ClientSession", _FakeSession)

    client = StdioMcpClient(_make_spec())
    await client.start()
    tools = await client.list_tools()
    await client.stop()

    assert captured["initialized"] is True
    assert captured["session_entered"] is True
    assert captured["streams"] == ("read_stream", "write_stream")
    assert captured["params"].command == "python"
    assert captured["params"].args == ["-m", "demo_server"]
    assert captured["params"].env == {"DEMO": "1"}
    assert tools[0].server_id == McpServerId("demo")
    assert tools[0].name == "add"
    assert tools[0].description == "Add two numbers"
    assert tools[0].input_schema == {"type": "object"}
    assert captured["session_closed"] is True
    assert captured["transport_closed"] is True


@pytest.mark.asyncio
async def test_stdio_mcp_client_call_tool_prefers_structured_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    @asynccontextmanager
    async def fake_stdio_client(params: object):
        yield ("read_stream", "write_stream")

    class _FakeSession:
        def __init__(self, read_stream: object, write_stream: object) -> None:
            return None

        async def __aenter__(self) -> "_FakeSession":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def initialize(self) -> None:
            return None

        async def call_tool(
            self, name: str, arguments: dict[str, Any] | None = None
        ) -> mcp_types.CallToolResult:
            captured["name"] = name
            captured["arguments"] = arguments
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text="ignored")],
                structuredContent={"sum": 8},
                isError=False,
            )

    monkeypatch.setattr(stdio_client_module, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(stdio_client_module, "ClientSession", _FakeSession)

    client = StdioMcpClient(_make_spec())
    await client.start()
    result = await client.call_tool("add", {"a": 5, "b": 3})
    await client.stop()

    assert captured["name"] == "add"
    assert captured["arguments"] == {"a": 5, "b": 3}
    assert result == {"sum": 8}


@pytest.mark.asyncio
async def test_stdio_mcp_client_raises_for_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def fake_stdio_client(params: object):
        yield ("read_stream", "write_stream")

    class _FakeSession:
        def __init__(self, read_stream: object, write_stream: object) -> None:
            return None

        async def __aenter__(self) -> "_FakeSession":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def initialize(self) -> None:
            return None

        async def call_tool(
            self, name: str, arguments: dict[str, Any] | None = None
        ) -> mcp_types.CallToolResult:
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text="boom")],
                isError=True,
            )

    monkeypatch.setattr(stdio_client_module, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(stdio_client_module, "ClientSession", _FakeSession)

    client = StdioMcpClient(_make_spec())
    await client.start()

    with pytest.raises(RuntimeError, match="boom"):
        await client.call_tool("explode", {})

    await client.stop()