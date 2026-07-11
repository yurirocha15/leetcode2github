"""
CLI helper functions
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import os
import signal
from collections.abc import Iterable, Mapping
from typing import Protocol

from leet2git.question_db import IdTitleMap, QuestionData


class _SourceConfig(Protocol):
    source_path: str


class _ConfigManager(Protocol):
    @property
    def config(self) -> _SourceConfig: ...

    def reset_config(self, repo_path: str, language: str, /) -> None: ...


class _QuestionMap(Protocol):
    def check_if_id_is_known(self, slug: str, /) -> bool: ...

    def set_id_title_map(self, id_title_map: IdTitleMap, /) -> None: ...

    def save(self) -> None: ...

    def get_id_from_title(self, slug: str, /) -> int | None: ...


class _IdTitleMapClient(Protocol):
    def get_id_title_map(self) -> IdTitleMap: ...


class _Joinable(Protocol):
    def join(self) -> object: ...


class _QuestionSink(Protocol):
    def add_question(self, question: QuestionData, /) -> None: ...


def mgr_init() -> None:
    """initializer for SyncManager"""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def reset_config(
    cm: _ConfigManager,
    source_repository: str,
    language: str,
    load_old: bool = True,
) -> None:
    """Reset the configuration file

    Args:
        cm (ConfigManager): the configuration manager
        source_repository (str): the path to the folder where the code will be saved
        language (str): the default language
        load_old (bool, optional): If true load old value from config. Defaults to True.
    """
    if not source_repository and load_old:
        source_repository = cm.config.source_path
    if not source_repository:
        source_repository = os.getcwd()
    cm.reset_config(source_repository, language)


def get_question_id(
    title_slug: str,
    qdb: _QuestionMap,
    lc: _IdTitleMapClient,
) -> int | None:
    """Get the question id from the title

    Args:
        title_slug (str): the title slug
        qdb (QuestionDB): the question database
        lc (LeetcodeClient): the leetcode client

    Returns:
        int | None: the question id, or None if not found
    """
    if not qdb.check_if_id_is_known(title_slug):
        qdb.set_id_title_map(lc.get_id_title_map())
        qdb.save()
    return qdb.get_id_from_title(title_slug)


def wait_to_finish_download(
    jobs: Iterable[_Joinable],
    ret_dict: Mapping[object, QuestionData],
    qdb: _QuestionSink,
) -> int:
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
