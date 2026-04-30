from pathlib import Path

from adomcore.app.settings import AppSettings


def test_app_settings_loads_plugin_config(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
plugins:
  plugin_dirs:
    - ./local_plugins
  config:
    searchxng:
      base_url: http://localhost:8080
""".strip(),
        encoding="utf-8",
    )

    settings = AppSettings.load(config_file)

    assert settings.plugins.plugin_dirs == ["./local_plugins"]
    assert settings.plugins.config["searchxng"]["base_url"] == "http://localhost:8080"
    assert settings.plugins.config["searchxng"].get("base_url") == (
        "http://localhost:8080"
    )
    assert settings.plugins.config["searchxng"].get("missing", "fallback") == "fallback"
