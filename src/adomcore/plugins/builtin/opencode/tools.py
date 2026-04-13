"""Builtin opencode plugin tools."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import httpx
from httpx import Timeout
from loguru import logger

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId
from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.plugins.context import PluginContext
from adomcore.utils import discover_random_unused_port, random_password

_PLUGIN_ID = PluginId("opencode")


def _as_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}


def _as_port_range(value: object) -> tuple[int, int]:
    if isinstance(value, tuple):
        items = cast(tuple[object, ...], value)
        if len(items) == 2:
            start, end = items
            if isinstance(start, int | str) and isinstance(end, int | str):
                return int(start), int(end)
    if isinstance(value, list):
        items = cast(list[object], value)
        if len(items) == 2:
            start, end = items
            if isinstance(start, int | str) and isinstance(end, int | str):
                return int(start), int(end)
    return (40000, 50000)


@dataclass
class _OpencodeSessionState:
    session_id: str | None = None
    selected_port: int | None = None
    password: str | None = None


class OpencodeToolset:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._state = _OpencodeSessionState()
        self._context: PluginContext | None = None

    def bind_context(self, context: PluginContext) -> OpencodeToolset:
        self._context = context
        return self

    def function_bindings(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="opencode_execute_task",
                    description=(
                        "Send a task to an opencode HTTP server. The first call can start "
                        "opencode serve automatically; later calls reuse the same live session."
                    ),
                    input_schema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Task or instruction to send to opencode.",
                            },
                            "new_session": {
                                "type": "boolean",
                                "description": "Force creation of a fresh opencode session instead of reusing the cached one.",
                                "default": False,
                            },
                            "session_title": {
                                "type": "string",
                                "description": "Optional title to use when a new opencode session is created.",
                            },
                        },
                        "required": ["prompt"],
                    },
                    source_plugin=_PLUGIN_ID,
                ),
                handler=self.execute_task,
            )
        ]

    async def execute_task(
        self,
        prompt: str,
        new_session: bool = False,
        session_title: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._execute_task_sync,
            prompt,
            new_session,
            session_title,
        )

    def _execute_task_sync(
        self,
        prompt: str,
        new_session: bool,
        session_title: str | None,
    ) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        server_started = False
        if not self._is_server_healthy():
            self._start_server()
            self._wait_for_server()
            server_started = True

        reused_session = False
        if new_session:
            self._state.session_id = None
        session_id = self._state.session_id
        if session_id and self._session_exists(session_id):
            reused_session = True
        else:
            session_id = self._create_session(session_title)
            self._state.session_id = session_id

        response = self._request_json(
            "POST",
            f"/session/{session_id}/message",
            body={
                "parts": [{"type": "text", "text": prompt}],
            },
        )
        return {
            "server_url": self._base_url,
            "server_started": server_started,
            "session_id": session_id,
            "reused_session": reused_session,
            "response": response,
        }

    @property
    def _base_url(self) -> str:
        configured = str(self._config.get("base_url", "")).strip()
        if configured:
            return configured.rstrip("/")
        hostname = str(self._config.get("hostname", "127.0.0.1")).strip() or "127.0.0.1"
        port = self._resolved_port()
        return f"http://{hostname}:{port}"

    def _resolved_port(self) -> int:
        configured_port = self._config.get("port")
        if configured_port not in (None, ""):
            return int(configured_port)
        if self._state.selected_port is None:
            port_range = _as_port_range(self._config.get("port_range", (40000, 50000)))
            self._state.selected_port = discover_random_unused_port(port_range)
        return self._state.selected_port

    def _resolved_password(self) -> str | None:
        configured_password = self._config.get("password")
        if configured_password not in (None, ""):
            return str(configured_password)
        if self._state.password is None:
            length = int(self._config.get("password_length", 32))
            self._state.password = random_password(length)
        return self._state.password

    def _is_server_healthy(self) -> bool:
        try:
            payload = self._request_json("GET", "/global/health")
        except OSError, ValueError, RuntimeError:
            return False
        return bool(_as_mapping(payload).get("healthy", False))

    def _wait_for_server(self) -> None:
        timeout_seconds = float(self._config.get("startup_timeout_seconds", 20))
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._is_server_healthy():
                return
            time.sleep(0.25)
        raise TimeoutError(
            f"Timed out waiting for opencode server at {self._base_url} to become healthy"
        )

    def _start_server(self) -> None:
        command = self._build_command()
        env = os.environ.copy()
        extra_env = self._config.get("env")
        if isinstance(extra_env, Mapping):
            typed_env = cast(Mapping[object, object], extra_env)
            env.update({str(key): str(value) for key, value in typed_env.items()})

        logger.debug(f"Starting opencode server with config: {self._config}")

        override_config = self._resolved_override_config()
        if override_config:
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps(
                self._merged_opencode_inline_config(
                    env.get("OPENCODE_CONFIG_CONTENT"),
                    override_config,
                )
            )
            logger.debug(
                "Generated opencode inline config: {}",
                override_config,
            )

        password = self._resolved_password()
        if password is not None:
            env["OPENCODE_SERVER_PASSWORD"] = str(password)

        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Unable to start opencode serve because the 'opencode' executable was not found"
            ) from exc

    @staticmethod
    def _merged_opencode_inline_config(
        existing_content: str | None,
        override: dict[str, Any],
    ) -> dict[str, Any]:
        if not existing_content:
            return dict(override)
        try:
            parsed = json.loads(existing_content)
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        merged = dict(cast(dict[str, Any], parsed))
        merged.update(override)
        return merged

    def _build_command(self) -> list[str]:
        executable = str(self._config.get("command", "opencode"))
        hostname = str(self._config.get("hostname", "127.0.0.1"))
        port = str(self._resolved_port())
        command = [executable, "serve", "--hostname", hostname, "--port", port]

        if bool(self._config.get("mdns", False)):
            command.append("--mdns")
        mdns_domain = str(self._config.get("mdns_domain", "")).strip()
        if mdns_domain:
            command.extend(["--mdns-domain", mdns_domain])
        cors = self._config.get("cors", [])
        if isinstance(cors, list):
            typed_cors = cast(list[object], cors)
            for origin in typed_cors:
                command.extend(["--cors", str(origin)])
        return command

    def _resolved_override_config(self) -> dict[str, Any]:
        explicit_override = self._config.get("override_config")
        if isinstance(explicit_override, Mapping):
            return dict(cast(Mapping[str, Any], explicit_override))

        override_model_id = str(self._config.get("override_model_id", "")).strip()
        if not override_model_id:
            return {}

        spec = self._resolve_model_spec(override_model_id)
        if spec is not None:
            return self._build_opencode_config_from_model_spec(spec)
        raise RuntimeError(
            f"Unable to resolve model spec for override_model_id {override_model_id}"
        )

    def _resolve_model_spec(self, model_id: str) -> ModelSpec | None:
        if self._context is None:
            return None
        try:
            return self._context.model_service.get(model_id)
        except KeyError:
            return None

    @staticmethod
    def _build_opencode_config_from_model_spec(spec: ModelSpec) -> dict[str, Any]:
        provider_id, model_value = OpencodeToolset._provider_and_model_for_spec(spec)
        provider_options: dict[str, Any] = dict(spec.extra_config)

        if spec.api_key not in (None, ""):
            provider_options["apiKey"] = spec.api_key
        if spec.api_base not in (None, ""):
            provider_options["baseURL"] = spec.api_base

        provider_entry: dict[str, Any] = {"options": provider_options}
        return {
            "model": model_value,
            "provider": {provider_id: provider_entry},
        }

    @staticmethod
    def _provider_and_model_for_spec(spec: ModelSpec) -> tuple[str, str]:
        if spec.provider == ModelProviderKind.ANTHROPIC:
            return "anthropic", f"anthropic/{spec.model}"
        return "openai", f"openai/{spec.model}"

    def _session_exists(self, session_id: str) -> bool:
        try:
            self._request_json("GET", f"/session/{session_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise RuntimeError(
                f"Failed to validate opencode session {session_id}: {exc}"
            ) from exc
        except OSError, ValueError:
            return False
        return True

    def _create_session(self, session_title: str | None) -> str:
        configured_title = str(self._config.get("session_title", "")).strip() or None
        title = session_title or configured_title
        payload = self._request_json(
            "POST",
            "/session",
            body={"title": title} if title else {},
        )
        session_id = str(_as_mapping(payload).get("id", "")).strip()
        if not session_id:
            raise ValueError("opencode server did not return a session id")
        return session_id

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = self._base_url + path

        headers = {
            "Accept": "application/json",
        }
        authorization = self._basic_auth_header()
        if authorization:
            headers["Authorization"] = authorization
        try:
            response = httpx.request(
                method,
                url,
                params=query,
                json=body,
                headers=headers,
                timeout=Timeout(None),
            )
            response.raise_for_status()
            raw = response.text
        except httpx.HTTPStatusError:
            raise
        except (httpx.RequestError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                f"Failed to contact opencode server at {url}: {exc}"
            ) from exc

        if not raw.strip():
            raise RuntimeError(
                f"Opencode server at {url} returned empty response; status code was {response.status_code}"
            )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
        finally:
            logger.debug(
                "Opencode server response: {} {} -> {}",
                method,
                url,
                json.dumps(raw, default=str),
            )

    def _basic_auth_header(self) -> str | None:
        password = self._config.get("password") or self._state.password
        if password in (None, ""):
            password = os.getenv("OPENCODE_SERVER_PASSWORD")
        if password in (None, ""):
            return None
        username = (
            self._config.get("username")
            or os.getenv("OPENCODE_SERVER_USERNAME")
            or "opencode"
        )
        token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        return f"Basic {token}"


def opencode_function_bindings(
    config: dict[str, Any] | None = None,
) -> list[FunctionBinding]:
    return OpencodeToolset(config).function_bindings()
