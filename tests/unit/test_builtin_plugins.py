import base64
import json
from pathlib import Path
from typing import Any

import pytest

from adomcore.domain.ids import PluginId
from adomcore.domain.models import ModelProviderKind, ModelSpec
from adomcore.plugins.context import PluginContext
from adomcore.services.capability_registry import CapabilityRegistry
from adomcore.services.model_service import ModelService
from adomcore.services.plugin_loader import PluginLoader
from adomcore.services.plugin_model_gateway import PluginModelGateway


def _fixed_port(_port_range: tuple[int, int] = (40000, 50000)) -> int:
    return 45678


def _fixed_password(_length: int = 32) -> str:
    return "AbC123XyZ789PasswordSafeToken000"


def test_plugin_loader_loads_builtin_searchxng_plugin() -> None:
    from adomcore.domain.plugins import PluginDescriptor

    loader = PluginLoader({"searchxng": {"base_url": "http://localhost:8080"}})
    plugin = loader.load(
        PluginDescriptor(
            id=PluginId("searchxng"),
            name="searchxng",
            version="0.1.0",
            description="",
            manifest_path=None,
        )
    )

    assert plugin.id == PluginId("searchxng")
    assert plugin.functions()[0].spec.name == "searchxng_search"


def test_plugin_loader_loads_builtin_local_fs_plugin() -> None:
    from adomcore.domain.plugins import PluginDescriptor

    plugin = PluginLoader().load(
        PluginDescriptor(
            id=PluginId("local_fs"),
            name="local_fs",
            version="0.1.0",
            description="",
            manifest_path=None,
        )
    )

    assert plugin.id == PluginId("local_fs")
    assert [binding.spec.name for binding in plugin.functions()] == [
        "read_file",
        "write_file",
        "list_dir",
    ]


def test_plugin_loader_loads_builtin_opencode_plugin() -> None:
    from adomcore.domain.plugins import PluginDescriptor

    plugin = PluginLoader(
        {"opencode": {"port": 4096, "override_model_id": "anthropic/claude-sonnet-4-5"}}
    ).load(
        PluginDescriptor(
            id=PluginId("opencode"),
            name="opencode",
            version="0.1.0",
            description="",
            manifest_path=None,
        )
    )

    assert plugin.id == PluginId("opencode")
    assert plugin.functions()[0].spec.name == "opencode_execute_task"


def test_opencode_tool_merges_override_model_into_inline_config() -> None:
    from adomcore.plugins.builtin.opencode.tools import OpencodeToolset

    merged = OpencodeToolset._merged_opencode_inline_config(  # type: ignore
        '{"autoupdate":true,"server":{"port":4096}}',
        {"model": "anthropic/claude-sonnet-4-5"},
    )

    assert merged == {
        "autoupdate": True,
        "server": {"port": 4096},
        "model": "anthropic/claude-sonnet-4-5",
    }


def test_opencode_tool_builds_override_config_from_adom_model_spec() -> None:
    from adomcore.plugins.builtin.opencode.tools import OpencodeToolset

    toolset = OpencodeToolset({"override_model_id": "main"})
    context = PluginContext(
        CapabilityRegistry(),
        model_gateway=PluginModelGateway(
            ModelService(
                [
                    ModelSpec(
                        id="main",
                        provider=ModelProviderKind.OPENAI_COMPATIBLE,
                        model="gpt-5.4",
                        context_window=32000,
                        api_base="https://ai.example.com/v1",
                        api_key="secret-key",
                        extra_config={"timeout": 1234},
                    )
                ],
                default_model_id="main",
            )
        ),
    )

    toolset.bind_context(context)

    assert toolset._resolved_override_config() == {  # type: ignore
        "model": "openai/gpt-5.4",
        "provider": {
            "openai": {
                "options": {
                    "timeout": 1234,
                    "apiKey": "secret-key",
                    "baseURL": "https://ai.example.com/v1",
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_searchxng_tool_uses_configured_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from adomcore.plugins.builtin.searchxng.tools import SearchXNGToolset

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "results": [
                        {
                            "title": "Example",
                            "url": "https://example.com",
                            "content": "snippet",
                            "engine": "mock",
                        }
                    ]
                }
            ).encode("utf-8")

    captured: dict[str, Any] = {}

    def _fake_urlopen(url: str, timeout: int) -> _Response:
        captured["url"] = url
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(
        "adomcore.plugins.builtin.searchxng.tools.urlopen", _fake_urlopen
    )
    toolset = SearchXNGToolset({"base_url": "http://localhost:8080"})

    result = await toolset.search("adom")

    assert captured["url"] == "http://localhost:8080/search?q=adom&format=json"
    assert result["result_count"] == 1
    assert result["results"][0]["title"] == "Example"


def test_ask_user_tool_returns_questionary_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from adomcore.plugins.builtin.ask_user.tools import (
        _ask_user,  # type: ignore[import]
    )

    class _Prompt:
        def ask(self) -> str:
            return "yes"

    def _fake_text(question: str) -> _Prompt:
        assert question == "Continue?"
        return _Prompt()

    monkeypatch.setattr("questionary.text", _fake_text)

    assert _ask_user("Continue?") == {"question": "Continue?", "answer": "yes"}


@pytest.mark.asyncio
async def test_opencode_execute_task_accepts_loaded_plugin_config_in_repl_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from adomcore.app.settings import AppSettings
    from adomcore.plugins.builtin.opencode.plugin import BuiltinOpencodePlugin
    from adomcore.services.plugin_manager import PluginManager
    from adomcore.services.tool_executor import ToolExecutor
    from adomcore.storage.json5_store import Json5Store
    from adomcore.storage.path_resolver import PathResolver
    from adomcore.storage.stores.plugin_store import PluginStore

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
plugins:
  config:
    opencode:
      hostname: 127.0.0.1
      port: 45678
      username: chensideyu
      password: configured-password
      session_title: Configured session
""".strip(),
        encoding="utf-8",
    )
    settings = AppSettings.load(config_file)
    registry = CapabilityRegistry()
    manager = PluginManager(
        PluginStore(PathResolver(tmp_path), Json5Store()),
        PluginLoader(),
        registry,
    )
    opencode_config = settings.plugins.config["opencode"]
    manager.activate_instance(BuiltinOpencodePlugin(opencode_config))  # type: ignore[arg-type]
    executor = ToolExecutor(registry)

    expected_auth = "Basic " + base64.b64encode(
        b"chensideyu:configured-password"
    ).decode("ascii")
    requests: list[tuple[str, str, dict[str, Any] | None]] = []

    class _Response:
        def __init__(self, payload: object) -> None:
            self.status_code = 200
            self.text = json.dumps(payload)

        def raise_for_status(self) -> None:
            return None

    def _fake_httpx_request(
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: object,
    ) -> _Response:
        assert isinstance(timeout, httpx.Timeout)
        assert params is None
        assert headers is not None
        assert headers["Authorization"] == expected_auth
        requests.append((method, url, json))

        if url.endswith("/global/health") and method == "GET":
            return _Response({"healthy": True})
        if url.endswith("/session") and method == "POST":
            assert json == {"title": "Configured session"}
            return _Response({"id": "sess_config"})
        if url.endswith("/session/sess_config/message") and method == "POST":
            assert json == {"parts": [{"type": "text", "text": "Write tests"}]}
            return _Response({"parts": [{"type": "text", "text": "done"}]})
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.httpx.request", _fake_httpx_request
    )

    result = await executor.execute("opencode_execute_task", {"prompt": "Write tests"})

    assert result["server_url"] == "http://127.0.0.1:45678"
    assert result["server_started"] is False
    assert result["session_id"] == "sess_config"
    assert result["reused_session"] is False
    assert requests == [
        ("GET", "http://127.0.0.1:45678/global/health", None),
        ("POST", "http://127.0.0.1:45678/session", {"title": "Configured session"}),
        (
            "POST",
            "http://127.0.0.1:45678/session/sess_config/message",
            {"parts": [{"type": "text", "text": "Write tests"}]},
        ),
    ]


@pytest.mark.asyncio
async def test_opencode_tool_starts_server_then_reuses_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from adomcore.plugins.builtin.opencode.tools import OpencodeToolset

    class _Response:
        def __init__(self, payload: object, status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code
            self.text = json.dumps(payload)

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                request = httpx.Request("GET", "http://localhost")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError(
                    "request failed",
                    request=request,
                    response=response,
                )

    health_attempts = 0
    created_sessions = 0
    posted_messages: list[dict[str, Any]] = []
    spawned_commands: list[list[str]] = []
    spawned_envs: list[dict[str, str]] = []

    def _fake_popen(command: list[str], **kwargs: Any) -> object:
        spawned_commands.append(command)
        spawned_envs.append(dict(kwargs["env"]))

        class _Process:
            pass

        return _Process()

    def _fake_httpx_request(
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: object,
    ) -> _Response:
        nonlocal health_attempts, created_sessions
        assert isinstance(timeout, httpx.Timeout)
        assert params is None
        data = json
        assert headers is not None

        if url.endswith("/global/health"):
            health_attempts += 1
            if health_attempts == 1:
                raise httpx.ConnectError(
                    "connection refused",
                    request=httpx.Request(method, url),
                )
            return _Response({"healthy": True, "version": "1.0.0"})
        if url.endswith("/session") and method == "POST":
            created_sessions += 1
            return _Response({"id": "sess_1"})
        if url.endswith("/session/sess_1") and method == "GET":
            return _Response({"id": "sess_1"})
        if url.endswith("/session/sess_1/message") and method == "POST":
            assert data is not None
            posted_messages.append(data)
            return _Response(
                {"info": {"id": "msg_1"}, "parts": [{"type": "text", "text": "done"}]}
            )
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.httpx.request", _fake_httpx_request
    )
    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.subprocess.Popen", _fake_popen
    )
    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.time.sleep",
        lambda _seconds: None,  # type: ignore[assignment]
    )
    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.discover_random_unused_port",
        _fixed_port,
    )
    monkeypatch.setattr(
        "adomcore.plugins.builtin.opencode.tools.random_password",
        _fixed_password,
    )

    toolset = OpencodeToolset(
        {
            "hostname": "127.0.0.1",
            "override_model_id": "main",
        }
    )
    toolset.bind_context(
        PluginContext(
            CapabilityRegistry(),
            model_gateway=PluginModelGateway(
                ModelService(
                    [
                        ModelSpec(
                            id="main",
                            provider=ModelProviderKind.OPENAI_COMPATIBLE,
                            model="gpt-5.4",
                            context_window=32000,
                            api_base="https://ai.example.com/v1",
                            api_key="secret-key",
                            extra_config={"timeout": 1234},
                        )
                    ],
                    default_model_id="main",
                )
            ),
        )
    )

    first = await toolset.execute_task("First task")
    second = await toolset.execute_task("Second task")

    assert spawned_commands == [
        ["opencode", "serve", "--hostname", "127.0.0.1", "--port", "45678"]
    ]
    assert (
        spawned_envs[0]["OPENCODE_SERVER_PASSWORD"]
        == "AbC123XyZ789PasswordSafeToken000"
    )
    assert json.loads(spawned_envs[0]["OPENCODE_CONFIG_CONTENT"]) == {
        "model": "openai/gpt-5.4",
        "provider": {
            "openai": {
                "options": {
                    "timeout": 1234,
                    "apiKey": "secret-key",
                    "baseURL": "https://ai.example.com/v1",
                }
            }
        },
    }
    assert created_sessions == 1
    assert first["server_started"] is True
    assert first["reused_session"] is False
    assert second["server_started"] is False
    assert second["reused_session"] is True
    assert first["server_url"] == "http://127.0.0.1:45678"
    assert posted_messages[0]["parts"][0]["text"] == "First task"
    assert posted_messages[1]["parts"][0]["text"] == "Second task"


def test_ssh_session_pool_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    from adomcore.plugins.builtin.ssh.tools import SSHSessionPool

    class _Stream:
        def __init__(self, data: str, exit_status: int = 0) -> None:
            self._data = data
            self.channel = self
            self._exit_status = exit_status

        def read(self) -> bytes:
            return self._data.encode("utf-8")

        def recv_exit_status(self) -> int:
            return self._exit_status

    class _Client:
        def __init__(self) -> None:
            self.connected = False
            self.closed = False

        def set_missing_host_key_policy(self, _policy: object) -> None:
            return None

        def connect(self, **kwargs: Any) -> None:
            self.connected = True
            self.kwargs = kwargs

        def exec_command(
            self, command: str, timeout: float
        ) -> tuple[None, _Stream, _Stream]:
            assert command == "pwd"
            assert timeout == 30
            return None, _Stream("/tmp\n"), _Stream("")

        def close(self) -> None:
            self.closed = True

    class _Paramiko:
        @staticmethod
        def AutoAddPolicy() -> object:
            return object()

        @staticmethod
        def SSHClient() -> _Client:
            return _Client()

    import sys

    sys.modules["paramiko"] = _Paramiko()  # type: ignore[assignment]

    pool = SSHSessionPool()
    opened = pool.open_session(host="localhost", username="fred")
    executed = pool.execute_command(opened["session_id"], "pwd")
    closed = pool.close_session(opened["session_id"])

    assert opened["username"] == "fred"
    assert executed["stdout"] == "/tmp\n"
    assert closed["status"] == "closed"


def test_local_fs_tools_read_write_and_list(tmp_path: Path) -> None:
    from adomcore.plugins.builtin.local_fs.tools import list_dir, read_file, write_file

    sample = tmp_path / "sample.txt"
    written = write_file(str(sample), "hello")
    read = read_file(str(sample))
    listed = list_dir(str(tmp_path))

    assert written == {"status": "written", "path": str(sample)}
    assert read == {"content": "hello"}
    assert "sample.txt" in listed["entries"]
