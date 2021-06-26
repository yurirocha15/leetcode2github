import os
import signal
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

import click
from git import Repo

from leet2git.leetcode_client import LeetcodeClient
from leet2git.question_db import QuestionData

T = TypeVar("T", bound="FileHandler")


class FileHandler(ABC):
    conversions = {
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

    def __new__(cls: Type[T], data: QuestionData, config: Dict[str, Any]) -> T:
        subclasses: Dict[str, FileHandler] = {
            l: subclass for subclass in cls.__subclasses__() for l in subclass.languages
        }
        subclass = DefaultHandler
        if config["language"].lower() in subclasses:
            subclass = subclasses[config["language"].lower()]
        instance = super(FileHandler, subclass).__new__(subclass)
        instance.set_data(data, config)
        return instance

    def check_if_exists(self, language: str) -> bool:
        """Check if there is a handler for a given language

        Args:
            language (str): a programming language

        Returns:
            bool: true if there is a handler for the language
        """
        return language.lower() in self.conversions

    def generate_repo(self, folder_path: str):
        """Generates a git repository

        Args:
            folder_path (str): the path to the repository folder
        """
        _ = Repo.init(folder_path)
        with open(os.path.join(folder_path, "README.md"), "w") as _:
            pass
        os.makedirs(os.path.join(folder_path, "src"), exist_ok=True)

    @abstractmethod
    def set_data(self, question_data: QuestionData, config: Dict[str, Any]):
        raise NotImplementedError

    @abstractmethod
    def get_function_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_source(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generete_tests(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_submission_file(self):
        raise NotImplementedError


# helper function


def generate_files(
    args: Dict[int, QuestionData],
    qid: int,
    title_slug: str,
    lc: LeetcodeClient,
    timestamp: float,
    config: Dict[str, Any],
    code: Optional[str] = "",
):
    s = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        data, is_new = lc.get_question_data(qid, title_slug, config["language"], code)
    except ValueError as e:
        click.secho(e.args, fg="red")
        signal.signal(signal.SIGINT, s)
        return

    if is_new:
        # generate
        data.language = config["language"]
        data.creation_time = timestamp
        file_handler = FileHandler(data, config)
        data.function_name = file_handler.get_function_name()
        data.file_path = file_handler.generate_source()
        if data.inputs and data.outputs:
            data.test_file_path = file_handler.generete_tests()

        args[qid] = data
        click.secho(f"""The question "{qid}|{data.title}" was imported""")
    signal.signal(signal.SIGINT, s)


# child classes (need to be imported in order to be instantiated)

from leet2git.default_handler import DefaultHandler
from leet2git.python_handler import PythonHandler
