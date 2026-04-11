from pathlib import Path

from adomcore.domain.ids import PluginId
from adomcore.domain.plugins import PluginDescriptor
from adomcore.services.plugin_loader import PluginLoader


def test_load_instantiates_plugin_class_from_manifest_path(tmp_path: Path) -> None:
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text(
        """
class SamplePlugin:
    def __init__(self) -> None:
        self.created = True

    def setup(self, ctx) -> None:
        return None


plugin = SamplePlugin
""".strip()
    )

    descriptor = PluginDescriptor(
        id=PluginId("sample"),
        name="Sample",
        version="0.1.0",
        description="",
        entry_point="sample_plugin:plugin",
        builtin=False,
        manifest_path=str(tmp_path / "plugin.yaml"),
    )

    plugin = PluginLoader().load(descriptor)

    assert plugin.__class__.__name__ == "SamplePlugin"
    assert getattr(plugin, "created") is True


def test_load_builtin_instantiates_builtin_plugin() -> None:
    plugin = PluginLoader().load_builtin(PluginId("core_admin"))

    assert plugin.__class__.__name__ == "BuiltinCoreAdminPlugin"
