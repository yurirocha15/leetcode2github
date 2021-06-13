import os
import signal

from leet2git.config_manager import ConfigManager


def mgr_init():
    """initializer for SyncManager"""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def reset_config(cm: ConfigManager, source_repository: str, language: str):
    """Reset the configuration file

    Args:
        cm (ConfigManager): the configuration manager
        source_repository (str): the path to the folder where the code will be saved
        language (str): the default language
    """
    if not source_repository:
        source_repository = cm.get_config()["source_path"]
    if not source_repository:
        source_repository = os.getcwd()
    cm.reset_config(source_repository, language)
