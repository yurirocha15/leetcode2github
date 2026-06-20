import json

from leet2git.config_manager import AppConfig, ConfigManager, ConfigOverrides


def make_config_manager(tmp_path):
    manager = ConfigManager.__new__(ConfigManager)
    manager._config_path = str(tmp_path)
    manager._legacy_data_path = str(tmp_path / "data")
    manager._config_file = str(tmp_path / "config.json")
    manager._config = None
    return manager


def test_app_config_defaults_are_validated():
    config = AppConfig(source_path="/tmp/solutions")

    assert config.language == "python3"
    assert config.source_path == "/tmp/solutions"
    assert config.readme.show_difficulty is True
    assert config.source_code.add_description is True
    assert config.test_code.generate_tests is True


def test_load_config_validates_json_and_applies_overrides(tmp_path):
    manager = make_config_manager(tmp_path)
    with open(manager._config_file, "w", encoding="UTF8") as file:
        json.dump(
            {
                "language": "python3",
                "source_path": "/tmp/old",
                "readme": {"show_difficulty": False, "show_category": True},
                "source_code": {"add_description": False},
                "test_code": {"generate_tests": True},
            },
            file,
        )

    manager.load_config(ConfigOverrides(language="rust", source_path="/tmp/new"))

    assert manager.config.language == "rust"
    assert manager.config.source_path == "/tmp/new"
    assert manager.config.legacy_data_path == str(tmp_path / "data")
    assert manager.config.readme.show_difficulty is False
    assert manager.config.source_code.add_description is False


def test_reset_config_writes_user_editable_json_without_data_path(tmp_path, monkeypatch):
    manager = make_config_manager(tmp_path)
    monkeypatch.setattr("leet2git.config_manager.click.edit", lambda **_: None)

    manager.reset_config("/tmp/solutions", "python3")

    with open(manager._config_file, encoding="UTF8") as file:
        saved_config = json.load(file)

    assert saved_config["source_path"] == "/tmp/solutions"
    assert saved_config["language"] == "python3"
    assert "legacy_data_path" not in saved_config
    assert manager.config.legacy_data_path == str(tmp_path / "data")
