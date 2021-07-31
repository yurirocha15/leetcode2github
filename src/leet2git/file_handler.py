"""
Abstract class that defines the file handlers
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import os
import signal
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

import click
from git import Repo

from leet2git.leetcode_client import LeetcodeClient
from leet2git.question_db import QuestionData

T = TypeVar("T", bound="FileHandler")


class FileHandler(ABC):
    """Abstract class for file handlers

    Attributes:
        conversions (Dict[str, Dict[str, str]]): Variables that change with each language.
        languages (List[str]): List of languages this handler generates files to
    """

    languages: List[str] = []
    conversions: Dict[str, Dict[str, str]] = {
        "bash": {"extension": ".sh", "comment": "#"},
        "c": {"extension": ".c", "comment": "//"},
        "cpp": {"extension": ".cpp", "comment": "//"},
        "csharp": {"extension": ".cs", "comment": "//"},
        "golang": {"extension": ".go", "comment": "//"},
        "java": {"extension": ".java", "comment": "//"},
        "javascript": {"extension": ".js", "comment": "//"},
        "kotlin": {"extension": ".kt", "comment": "//"},
        "mysql": {"extension": ".sql", "comment": "--"},
        "php": {"extension": ".php", "comment": "//"},
        "python": {"extension": ".py", "comment": "#"},
        "python3": {"extension": ".py", "comment": "#"},
        "ruby": {"extension": ".rb", "comment": "#"},
        "rust": {"extension": ".rs", "comment": "//"},
        "scala": {"extension": ".scala", "comment": "//"},
        "swift": {"extension": ".swift", "comment": "//"},
    }

    @classmethod
    def get_handler_type(cls: Type[T], config: Dict[str, Any]) -> Type[T]:
        """Returns the type of the correct subclass

        Args:
            cls (Type[FileHandler]): this class type
            config (Dict[str, Any]): the user config

        Returns:
            Type[FileHandler]: the type of the correct subclass
        """
        subclasses: Dict[str, Type[T]] = {
            language: subclass for subclass in cls.__subclasses__() for language in subclass.languages
        }
        subclass: Type[T] = DefaultHandler
        if config["language"].lower() in subclasses:
            subclass = subclasses[config["language"].lower()]
        return subclass

    def check_if_exists(self, language: str) -> bool:
        """Check if there is a handler for a given language

        Args:
            language (str): a programming language

        Returns:
            bool: true if there is a handler for the language
        """
        return language.lower() in self.conversions

    def generate_repo(self, folder_path: str) -> None:
        """Generates a git repository

        Args:
            folder_path (str): the path to the repository folder
        """
        _ = Repo.init(folder_path)
        with open(os.path.join(folder_path, "README.md"), "w") as _:
            pass
        os.makedirs(os.path.join(folder_path, "src"), exist_ok=True)

    @abstractmethod
    def set_data(self, question_data: QuestionData, config: Dict[str, Any]) -> None:
        """Abstract method definition

        Raises:
            NotImplementedError: should be implemented by child classes
        """
        raise NotImplementedError

    @abstractmethod
    def get_function_name(self) -> str:
        """Abstract method definition

        Raises:
            NotImplementedError: should be implemented by child classes
        """
        raise NotImplementedError

    @abstractmethod
    def generate_source(self) -> str:
        """Abstract method definition

        Raises:
            NotImplementedError: should be implemented by child classes
        """
        raise NotImplementedError

    @abstractmethod
    def generete_tests(self) -> str:
        """Abstract method definition

        Raises:
            NotImplementedError: should be implemented by child classes
        """
        raise NotImplementedError

    @abstractmethod
    def generate_submission_file(self) -> None:
        """Abstract method definition

        Raises:
            NotImplementedError: should be implemented by child classes
        """
        raise NotImplementedError


# helper function
# pylint: disable=abstract-class-instantiated


def create_file_handler(data: QuestionData, config: Dict[str, Any]) -> FileHandler:
    """Create an instance of a File Handler

    Args:
        data (QuestionData): the question data
        config (Dict[str, Any]): the user configuration

    Returns:
        FileHandler: [description]
    """
    handler_type: Type[FileHandler] = FileHandler.get_handler_type(config)
    file_handler = super(FileHandler, handler_type).__new__(handler_type)
    file_handler.set_data(data, config)
    return file_handler


def generate_files(
    args: Dict[int, QuestionData],
    qid: int,
    title_slug: str,
    lc: LeetcodeClient,
    timestamp: float,
    config: Dict[str, Any],
    code: Optional[str] = "",
) -> None:
    """Auxiliar function to generate the question files

    Args:
        args (Dict[int, QuestionData]): a dictionary managed by the subprocess manager
        qid (int): the question id
        title_slug (str): the question title-slug property
        lc (LeetcodeClient): LeetcodeClient object
        timestamp (float): the time the question was generated
        config (Dict[str, Any]): the user config
        code (Optional[str], optional): the question solution. Defaults to "".
    """
    s = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        data, is_new = lc.get_question_data(qid, title_slug, config["language"], code)
    except ValueError as e:
        click.secho(e.args, fg="red")
        click.secho(traceback.format_exc())
        signal.signal(signal.SIGINT, s)
        return

    if is_new:
        # generate
        data.language = config["language"]
        data.creation_time = timestamp
        file_handler = create_file_handler(data, config)
        data.function_name = file_handler.get_function_name()
        data.file_path = file_handler.generate_source()
        if data.inputs and data.outputs:
            data.test_file_path = file_handler.generete_tests()

        args[qid] = data
        click.secho(f"""The question "{qid}|{data.title}" was imported""")
    signal.signal(signal.SIGINT, s)


# child classes (need to be imported in order to be instantiated)
# pylint: disable=wrong-import-position disable=unused-import
from leet2git.default_handler import DefaultHandler  # noqa
from leet2git.python_handler import PythonHandler  # noqa
