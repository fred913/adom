"""Canonical path resolver — single source of truth for all data paths."""

from pathlib import Path

from adomcore.domain.ids import CronJobId, McpServerId, PluginId, ThreadId


class PathResolver:
    """Derives every data-file path from a single root directory."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    # ── agent ────────────────────────────────────────────────────────────
    @property
    def agent_state(self) -> Path:
        return self._root / "agent" / "state.json5"

    @property
    def agent_profile(self) -> Path:
        return self._root / "agent" / "profile.json5"

    # ── threads ──────────────────────────────────────────────────────────
    def thread_dir(self, tid: ThreadId) -> Path:
        return self._root / "threads" / str(tid)

    def thread_events(self, tid: ThreadId) -> Path:
        return self.thread_dir(tid) / "events.jsonl"

    def thread_compact(self, tid: ThreadId) -> Path:
        return self.thread_dir(tid) / "compact.json5"

    def thread_meta(self, tid: ThreadId) -> Path:
        return self.thread_dir(tid) / "meta.json5"

    # ── plugins ──────────────────────────────────────────────────────────
    @property
    def plugin_registry(self) -> Path:
        return self._root / "plugins" / "registry.json5"

    def plugin_dir(self, pid: PluginId) -> Path:
        return self._root / "plugins" / "installed" / str(pid)

    def plugin_state(self, pid: PluginId) -> Path:
        return self.plugin_dir(pid) / "state.json5"

    def plugin_manifest(self, pid: PluginId) -> Path:
        return self.plugin_dir(pid) / "manifest.yaml"

    # ── skills ───────────────────────────────────────────────────────────
    @property
    def skills_file(self) -> Path:
        return self._root / "agent" / "skills.json5"

    # ── mcp ──────────────────────────────────────────────────────────────
    @property
    def mcp_servers(self) -> Path:
        return self._root / "mcp" / "servers.json5"

    def mcp_discovered_tools(self, sid: McpServerId | None = None) -> Path:
        if sid is not None:
            return self._root / "mcp" / f"tools_{sid}.json5"
        return self._root / "mcp" / "discovered_tools.json5"

    # ── scheduler ────────────────────────────────────────────────────────
    @property
    def cron_jobs(self) -> Path:
        return self._root / "scheduler" / "jobs.json5"

    @property
    def cron_history(self) -> Path:
        return self._root / "scheduler" / "history.jsonl"

    def cron_job_dir(self, jid: CronJobId) -> Path:
        return self._root / "scheduler" / str(jid)

    # ── runtime ──────────────────────────────────────────────────────────
    @property
    def runtime_boot(self) -> Path:
        return self._root / "runtime" / "boot.json5"

    @property
    def runtime_health(self) -> Path:
        return self._root / "runtime" / "health.json5"

    @property
    def runtime_locks_dir(self) -> Path:
        return self._root / "runtime" / "locks"

    # ── logs ─────────────────────────────────────────────────────────────
    @property
    def log_runtime(self) -> Path:
        return self._root / "logs" / "runtime.jsonl"

    @property
    def log_api(self) -> Path:
        return self._root / "logs" / "api.jsonl"

    @property
    def log_errors(self) -> Path:
        return self._root / "logs" / "errors.jsonl"
