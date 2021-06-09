import json
import os
import subprocess
from typing import Any, Dict

import appdirs


class ConfigManager:
    """Manages the user configuration files"""

    def __init__(self):
        ad = appdirs.AppDirs(appname="leet2git", appauthor=False)
        self._config_path = ad.user_config_dir
        self._data_path = ad.user_data_dir
        self._config_file = os.path.join(self._config_path, "config.json")
        os.makedirs(self._config_path, exist_ok=True)
        os.makedirs(self._data_path, exist_ok=True)

    def get_config(self) -> Dict[str, Any]:
        """Return the user configuration

        Returns:
            Dict[str, Any]: the user configuration
        """
        with open(self._config_file, "r") as file:
            config = json.load(file)
        config["data_path"] = self._data_path
        return config

    def get_editor(self) -> str:
        """Return the default editor

        Returns:
            str: the default editor
        """
        return os.environ.get("HGEDITOR") or os.environ.get("VISUAL") or os.environ.get("EDITOR", "vi")

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
        }
        with open(self._config_file, "w", encoding="UTF8") as file:
            json.dump(config_options, file, indent=4)

        self.edit_config()

    def edit_config(self):
        """Opens the configuration file on the default editor"""
        editor = self.get_editor()
        try:
            subprocess.call('%s "%s"' % (editor, self._config_file), shell=True)
        except Exception as e:
            print(e.args)


if __name__ == "__main__":
    cm = ConfigManager()
    cm.reset_config()
