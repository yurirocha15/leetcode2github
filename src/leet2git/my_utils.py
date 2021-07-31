"""
My util functions
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import os
import signal
from multiprocessing import Process
from typing import Any, Dict, List

from leet2git.config_manager import ConfigManager
from leet2git.leetcode_client import LeetcodeClient
from leet2git.question_db import QuestionDB


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


def get_question_id(title_slug: str, qdb: QuestionDB, lc: LeetcodeClient) -> int:
    """Get the question ID give the title slug

    Args:
        title_slug (str): the title slug
        qdb (QuestionDB): the question database
        lc (LeetcodeClient): the leetcode client

    Returns:
        int: the question id
    """
    qid: int = -1
    if qdb.check_if_id_is_known(title_slug):
        qid = qdb.get_id_from_title(title_slug)
    else:
        qdb.set_id_title_map(lc.get_id_title_map())
        qdb.save()
        qid = qdb.get_id_from_title(title_slug)
    return qid


def wait_to_finish_download(jobs: List[Process], ret_dict: Dict[Any, Any], qdb: QuestionDB) -> int:
    """Wait until every subprocess finishes

    Args:
        jobs (List[Process]): a list of subprocesses
        ret_dict (Dict[Any, Any]): the shared memory used to communicate with the subprocesses
        qdb (QuestionDB): the questionDB

    Returns:
        int: how may questions were imported in this batch
    """
    imported_cnt: int = 0
    for p in jobs:
        p.join()

    for data in ret_dict.values():
        qdb.add_question(data)
        imported_cnt += 1

    return imported_cnt
