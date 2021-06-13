import json
import os
from typing import Any, Dict, Optional

import appdirs
import click


class ConfigManager:
    """Manages the user configuration files"""

    def __init__(self):
        ad = appdirs.AppDirs(appname="leet2git", appauthor=False)
        self._config_path = ad.user_config_dir
        self._data_path = ad.user_data_dir
        self._config_file = os.path.join(self._config_path, "config.json")
        self.config: Dict[str, Any] = {}
        os.makedirs(self._config_path, exist_ok=True)
        os.makedirs(self._data_path, exist_ok=True)
        if not os.path.isfile(self._config_file):
            self.reset_config("")

    def load_config(self, override_config: Optional[Dict[str, Any]] = {}):
        """Loads the configuration

        Args:
            override_config (Optional[Dict[str, Any]]): values that should be overriden. Defaults to an empty dict.
        """
        with open(self._config_file, "r") as file:
            self.config = json.load(file)
        self.config["data_path"] = self._data_path
        for key, value in override_config.items():
            self.config[key] = value

    def get_config(self) -> Dict[str, Any]:
        """Return the user configuration

        Returns:
            Dict[str, Any]: the user configuration
        """
        return self.config

    def reset_config(self, repo_path: str, language: str = "python3"):
        """Resets the config and open it on the default editor

        Args:
            repo_path (str): the path to the folder where the code will be saved
            language (str, optional): the default language. Defaults to "python3".
        """
        config_options = {
            "language": language,
            "source_path": repo_path,
            "readme": {
                "show_difficulty": True,
                "show_category": True,
            },
            "source_code": {
                "add_description": True,
            },
            "test_code": {
                "generate_tests": True,
            },
        }
        with open(self._config_file, "w", encoding="UTF8") as file:
            json.dump(config_options, file, indent=4)

        click.edit(filename=self._config_file, extension=".json")
        click.secho(f"You can also edit the configuration manually. File Location: {self._config_file}")


if __name__ == "__main__":
    cm = ConfigManager()
    cm.reset_config()
