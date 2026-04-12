from pathlib import Path

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor
from adomcore.services.plugin_loader import PluginLoader


def test_load_instantiates_plugin_class_from_manifest_path(tmp_path: Path) -> None:
    plugin_file = tmp_path / "plugin.py"
    plugin_file.write_text(
        """
class SamplePlugin:
    plugin_id = 'sample'
    plugin_name = 'Sample'
    plugin_description = ''

    def __init__(self) -> None:
        self.created = True

    def functions(self):
        return []

    def skills(self):
        return []

    def system_prompt(self):
        return ''


plugin = SamplePlugin
""".strip()
    )

    descriptor = PluginDescriptor(
        id=PluginId("sample"),
        name="Sample",
        version="0.1.0",
        description="",
        manifest_path=str(tmp_path / "plugin.yaml"),
    )

    plugin = PluginLoader().load(descriptor)

    assert plugin.__class__.__name__ == "SamplePlugin"
    assert getattr(plugin, "created") is True
    assert plugin.id == PluginId("sample")
    assert plugin.name == "Sample"


def test_builtin_repo_plugin_uses_class_metadata() -> None:
    from adomcore.plugins.builtin.core_admin.plugin import BuiltinCoreAdminPlugin

    plugin = BuiltinCoreAdminPlugin()

    assert plugin.id == PluginId("core_admin")
    assert plugin.name == "core_admin"


def test_plugin_loader_loads_builtin_plugin_without_manifest_path() -> None:
    from adomcore.domain.plugins import PluginDescriptor

    plugin = PluginLoader({"searchxng": {"base_url": "http://localhost:8080"}}).load(
        PluginDescriptor(
            id=PluginId("searchxng"),
            name="searchxng",
            version="0.1.0",
            description="",
            manifest_path=None,
        )
    )

    assert plugin.id == PluginId("searchxng")
    assert plugin.name == "searchxng"
