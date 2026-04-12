import json
from pathlib import Path
from typing import Any

import pytest

from adomcore.domain.ids import PluginId
from adomcore.services.plugin_loader import PluginLoader


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
