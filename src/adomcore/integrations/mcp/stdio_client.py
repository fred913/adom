"""Stdio MCP client backed by the official MCP Python SDK."""

import json
from contextlib import AsyncExitStack
from typing import Any, Protocol

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp import types as mcp_types
from mcp.client.stdio import stdio_client

from adomcore.domain.mcp import McpServerSpec, McpToolSpec


class McpClientProtocol(Protocol):
    async def stop(self) -> None: ...

    async def list_tools(self) -> list[McpToolSpec]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class StdioMcpClient:
    def __init__(self, spec: McpServerSpec) -> None:
        self._spec = spec
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def start(self) -> None:
        if self._session is not None:
            return

        exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=self._spec.command,
                        args=self._spec.args,
                        env=self._spec.env,
                    )
                )
            )
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except Exception:
            await exit_stack.aclose()
            raise

        self._exit_stack = exit_stack
        self._session = session
        logger.debug("MCP process started: {}", self._spec.id)

    async def stop(self) -> None:
        exit_stack = self._exit_stack
        self._exit_stack = None
        self._session = None
        if exit_stack is not None:
            await exit_stack.aclose()

    def _require_session(self) -> ClientSession:
        session = self._session
        if session is None:
            raise RuntimeError(f"MCP server not started: {self._spec.id}")
        return session

    async def list_tools(self) -> list[McpToolSpec]:
        result = await self._require_session().list_tools()
        tools: list[McpToolSpec] = []
        for t in result.tools:
            tools.append(
                McpToolSpec(
                    server_id=self._spec.id,
                    name=t.name,
                    description=t.description or "",
                    input_schema=t.inputSchema or {},
                )
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._require_session().call_tool(name, arguments=arguments)
        if result.isError:
            raise RuntimeError(self._render_error(result))
        return self._normalise_call_result(result)

    def _render_error(self, result: mcp_types.CallToolResult) -> str:
        payload = self._normalise_call_result(result)
        if isinstance(payload, str):
            return payload
        try:
            return json.dumps(payload, ensure_ascii=False)
        except TypeError:
            return str(payload)

    def _normalise_call_result(self, result: mcp_types.CallToolResult) -> Any:
        if result.structuredContent is not None:
            return result.structuredContent

        content = [self._normalise_content_item(item) for item in result.content]
        if len(content) == 1:
            return content[0]
        return content

    def _normalise_content_item(self, item: object) -> Any:
        if isinstance(item, mcp_types.TextContent):
            return item.text
        if isinstance(item, mcp_types.ImageContent):
            return {
                "type": "image",
                "data": item.data,
                "mimeType": item.mimeType,
            }
        if isinstance(item, mcp_types.EmbeddedResource):
            resource = item.resource
            if isinstance(resource, mcp_types.TextResourceContents):
                return {
                    "uri": str(resource.uri),
                    "mimeType": resource.mimeType,
                    "text": resource.text,
                }
            assert isinstance(resource, mcp_types.BlobResourceContents)
            return {
                "uri": str(resource.uri),
                "mimeType": resource.mimeType,
                "blob": resource.blob,
            }
        if isinstance(item, mcp_types.ContentBlock):
            return item.model_dump(by_alias=True, exclude_none=True)
        return item
