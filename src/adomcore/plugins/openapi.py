"""Helpers for building plugins from OpenAPI specifications."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from adomcore.domain.capabilities import FunctionSpec
from adomcore.domain.ids import PluginId
from adomcore.plugins.context import PluginContext


def _safe_name(method: str, path: str) -> str:
    cleaned = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{method.lower()}_{cleaned or 'root'}"


def _merge_parameter_schema(
    parameters: list[dict[str, Any]],
) -> tuple[dict[str, Any], set[str]]:
    properties: dict[str, Any] = {}
    required: set[str] = set()
    for param in parameters:
        name = str(param.get("name", "")).strip()
        if not name:
            continue
        schema = dict(param.get("schema", {"type": "string"}))
        properties[name] = schema
        if bool(param.get("required", False)):
            required.add(name)
    return properties, required


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(cast(Mapping[str, Any], value))
    return {}


@dataclass(frozen=True)
class OpenApiOperation:
    operation_id: str
    method: str
    path: str
    description: str
    input_schema: dict[str, Any]


class OpenApiPlugin:
    def __init__(
        self,
        *,
        plugin_id: str,
        spec: dict[str, Any],
        base_url: str,
        auth_headers: dict[str, str] | None = None,
    ) -> None:
        self._plugin_id = PluginId(plugin_id)
        self._spec = spec
        self._base_url = base_url.rstrip("/")
        self._auth_headers = auth_headers or {}

    def setup(self, ctx: PluginContext) -> None:
        for operation in self._iter_operations():
            ctx.register_function(
                FunctionSpec(
                    name=operation.operation_id,
                    description=operation.description,
                    input_schema=operation.input_schema,
                    source_plugin=self._plugin_id,
                ),
                self._make_handler(operation),
            )

    def _iter_operations(self) -> list[OpenApiOperation]:
        operations: list[OpenApiOperation] = []
        paths = _as_dict(self._spec.get("paths", {}))
        for path_obj, path_item_obj in paths.items():
            path = str(path_obj)
            path_item = _as_dict(path_item_obj)
            if not path_item:
                continue
            for method_obj, raw_operation_obj in path_item.items():
                method = str(method_obj)
                raw_operation = _as_dict(raw_operation_obj)
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if not raw_operation:
                    continue
                operation_id = str(
                    raw_operation.get("operationId") or _safe_name(method, path)
                )
                summary = str(
                    raw_operation.get("summary")
                    or raw_operation.get("description")
                    or operation_id
                )
                parameters_raw = raw_operation.get("parameters", [])
                parameters: list[dict[str, Any]] = []
                if isinstance(parameters_raw, list):
                    for param in cast(list[object], parameters_raw):
                        if isinstance(param, Mapping):
                            parameters.append(dict(cast(Mapping[str, Any], param)))
                properties, required = _merge_parameter_schema(parameters)
                request_body = _as_dict(raw_operation.get("requestBody", {}))
                content = _as_dict(request_body.get("content", {}))
                json_content = _as_dict(content.get("application/json", {}))
                body_schema = _as_dict(json_content.get("schema"))
                if body_schema:
                    properties["body"] = body_schema
                    if request_body.get("required"):
                        required.add("body")
                input_schema: dict[str, Any] = {
                    "type": "object",
                    "properties": properties,
                }
                if required:
                    input_schema["required"] = sorted(required)
                operations.append(
                    OpenApiOperation(
                        operation_id=operation_id,
                        method=method.upper(),
                        path=path,
                        description=summary,
                        input_schema=input_schema,
                    )
                )
        return operations

    def _make_handler(self, operation: OpenApiOperation):
        async def handler(**kwargs: Any) -> dict[str, Any]:
            return await asyncio.to_thread(self._execute_http, operation, kwargs)

        return handler

    def _execute_http(
        self, operation: OpenApiOperation, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        path = operation.path
        query_params: dict[str, Any] = {}
        for key, value in arguments.items():
            placeholder = "{" + key + "}"
            if placeholder in path:
                path = path.replace(placeholder, str(value))
            elif key != "body" and value is not None:
                query_params[key] = value

        url = self._base_url + path
        if query_params:
            url = url + "?" + urlencode(query_params, doseq=True)

        headers = {"Content-Type": "application/json", **self._auth_headers}
        body_value = arguments.get("body")
        data = None
        if body_value is not None:
            data = json.dumps(body_value).encode("utf-8")

        req = Request(url=url, method=operation.method, headers=headers, data=data)
        with urlopen(req, timeout=15) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            parsed_body: Any
            try:
                parsed_body = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed_body = raw_body
            return {
                "status": getattr(response, "status", 200),
                "url": url,
                "method": operation.method,
                "body": parsed_body,
            }
