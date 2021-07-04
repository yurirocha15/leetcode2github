import os
import signal
from typing import Any, Dict

from leet2git.config_manager import ConfigManager


def mgr_init():
    """initializer for SyncManager"""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def reset_config(cm: ConfigManager, source_repository: str, language: str, load_old: bool = True):
    """Reset the configuration file

    Args:
        cm (ConfigManager): the configuration manager
        source_repository (str): the path to the folder where the code will be saved
        language (str): the default language
        load_old (bool, optional): If true load old value from config. Defaults to True.
    """
    if not source_repository and load_old:
        source_repository = cm.config["source_path"]
    if not source_repository:
        source_repository = os.getcwd()
    cm.reset_config(source_repository, language)
