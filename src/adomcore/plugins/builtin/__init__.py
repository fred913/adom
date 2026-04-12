"""Builtin plugins."""

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor


def builtin_plugin_descriptors() -> list[PluginDescriptor]:
    builtin_ids = [
        "core_admin",
        "cron",
        "memory_admin",
        "searchxng",
        "ask_user",
        "ssh",
        "local_fs",
    ]
    return [
        PluginDescriptor(
            id=PluginId(plugin_id),
            name=plugin_id,
            version="0.1.0",
            description="",
            manifest_path=None,
            enabled=True,
        )
        for plugin_id in builtin_ids
    ]
