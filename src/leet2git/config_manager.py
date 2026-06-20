"""
Manages the configuration files
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import json
import os

import click
from platformdirs import PlatformDirs
from pydantic import BaseModel, ConfigDict, Field


class ReadmeConfig(BaseModel):
    """README generation settings."""

    model_config = ConfigDict(validate_assignment=True)

    show_difficulty: bool = True
    show_category: bool = True


class SourceCodeConfig(BaseModel):
    """Source file generation settings."""

    model_config = ConfigDict(validate_assignment=True)

    add_description: bool = True


class TestCodeConfig(BaseModel):
    """Test file generation settings."""

    model_config = ConfigDict(validate_assignment=True)

    generate_tests: bool = True


class AppConfig(BaseModel):
    """Validated leet2git configuration."""

    model_config = ConfigDict(validate_assignment=True)

    language: str = "python3"
    source_path: str = ""
    legacy_data_path: str = ""
    readme: ReadmeConfig = Field(default_factory=ReadmeConfig)
    source_code: SourceCodeConfig = Field(default_factory=SourceCodeConfig)
    test_code: TestCodeConfig = Field(default_factory=TestCodeConfig)


class ConfigOverrides(BaseModel):
    """Typed command-line configuration overrides."""

    model_config = ConfigDict(validate_assignment=True)

    language: str | None = None
    source_path: str | None = None


class ConfigManager:
    """Manages the user configuration files"""

    def __init__(self):
        dirs = PlatformDirs(appname="leet2git", appauthor=False)
        self._config_path = dirs.user_config_dir
        self._legacy_data_path = dirs.user_data_dir
        self._config_file = os.path.join(self._config_path, "config.json")
        self._config: AppConfig | None = None
        os.makedirs(self._config_path, exist_ok=True)
        os.makedirs(self._legacy_data_path, exist_ok=True)
        if not os.path.isfile(self._config_file):
            self.reset_config("", edit=False)

    @property
    def config(self) -> AppConfig:
        """The user configuration

        Returns:
            AppConfig: the user configuration
        """
        if not self._config:
            return AppConfig(legacy_data_path=self._legacy_data_path)
        return self._config

    def load_config(self, override_config: ConfigOverrides | None = None):
        """Loads the configuration

        Args:
            override_config (Optional[ConfigOverrides]): values that should be overridden.
            Defaults to an empty dict.
        """
        if not override_config:
            override_config = ConfigOverrides()
        with open(self._config_file) as file:
            config = AppConfig.model_validate_json(file.read())
        self._config = config.model_copy(
            update={
                "legacy_data_path": self._legacy_data_path,
                **override_config.model_dump(exclude_none=True),
            }
        )

    def reset_config(self, repo_path: str, language: str = "python3", edit: bool = True):
        """Resets the config and open it on the default editor

        Args:
            repo_path (str): the path to the folder where the code will be saved
            language (str, optional): the default language. Defaults to "python3".
        """
        self._config = AppConfig(
            language=language,
            source_path=repo_path,
            legacy_data_path=self._legacy_data_path,
        )
        with open(self._config_file, "w", encoding="UTF8") as file:
            json.dump(
                self._config.model_dump(mode="json", exclude={"legacy_data_path"}),
                file,
                indent=4,
            )

        if edit:
            click.edit(filename=self._config_file, extension=".json")
            click.secho(
                f"You can also edit the configuration manually. File Location: {self._config_file}"
            )


if __name__ == "__main__":
    cm = ConfigManager()
    cm.reset_config(repo_path="")
