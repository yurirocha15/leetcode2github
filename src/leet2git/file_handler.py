"""
Abstract class that defines the file handlers
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import os
import signal
import subprocess
from abc import ABC, abstractmethod
from collections.abc import MutableMapping
from pathlib import Path
from typing import Protocol

import click

from leet2git.config_manager import AppConfig
from leet2git.question_db import QuestionData
from leet2git.test_harness import get_local_test_limitation

LANGUAGE_CONVERSIONS: dict[str, dict[str, str]] = {
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


class QuestionDataClient(Protocol):
    """Read-only client behavior needed during file generation."""

    def get_question_data(
        self,
        question_id: int,
        title_slug: str,
        language: str,
        code: str,
        /,
    ) -> QuestionData: ...


class FileHandler(ABC):
    """Abstract base class for file handlers."""

    languages: list[str] = []

    def check_if_exists(self, language: str) -> bool:
        """Check if there is a handler for a given language

        Args:
            language (str): a programming language

        Returns:
            bool: true if there is a handler for the language
        """
        return language.lower() in LANGUAGE_CONVERSIONS

    def generate_repo(self, folder_path: str) -> None:
        """Generates a git repository

        Args:
            folder_path (str): the path to the repository folder
        """
        try:
            subprocess.run(["git", "init", folder_path], check=True)
        except subprocess.CalledProcessError as e:
            raise click.ClickException(f"Failed to initialize git repository: {e}") from e
        with open(os.path.join(folder_path, "README.md"), "w") as _:
            pass
        os.makedirs(os.path.join(folder_path, "src"), exist_ok=True)

    def set_data(self, question_data: QuestionData, config: AppConfig) -> None:
        """Assign question data and configuration to the handler."""
        self.question_data = question_data
        self.config = config

    @abstractmethod
    def get_function_name(self) -> list[str]:
        """Return the list of function names found in the code template."""
        raise NotImplementedError

    @abstractmethod
    def generate_source(self) -> Path:
        """Generate and write the source file; return its relative path."""
        raise NotImplementedError

    @abstractmethod
    def generate_tests(self) -> str:
        """Generate and write the test file; return its relative path."""
        raise NotImplementedError

    @abstractmethod
    def generate_submission_file(self) -> str:
        """Generate the submission file content; return it as a string."""
        raise NotImplementedError

    def remove_test_entrypoint(self) -> None:
        """Remove any source entrypoint that targets a failed local test generation."""
        return None

    def _build_source_header(self) -> tuple[str, str, list[str]]:
        """Build the source file header block.

        Returns:
            tuple[str, str, list[str]]: (comment_char, extension, header_lines)
        """
        comment: str = LANGUAGE_CONVERSIONS[self.question_data.language]["comment"]
        extension: str = LANGUAGE_CONVERSIONS[self.question_data.language]["extension"]
        description = (
            [comment + " " + line + "\n" for line in self.question_data.description]
            if self.config.source_code.add_description
            else []
        )
        lines: list[str] = (
            [
                comment + f" @l2g {self.question_data.id} {self.question_data.language}\n",
                comment + f" [{self.question_data.id}] {self.question_data.title}\n",
                comment + f" Difficulty: {self.question_data.difficulty}\n",
                comment + f" {self.question_data.url}\n",
                comment + "\n",
            ]
            + description
            + [
                "\n",
                "\n",
            ]
        )
        return comment, extension, lines


# helper function
# pylint: disable=abstract-class-instantiated


def create_file_handler(data: QuestionData, config: AppConfig) -> FileHandler:
    """Create an instance of a File Handler

    Args:
         data (QuestionData): the question data
         config (AppConfig): the user configuration

    Returns:
         FileHandler: the initialized file handler
    """
    from leet2git.handler_registry import get_handler_type

    handler_type: type[FileHandler] = get_handler_type(config.language)
    file_handler = super(FileHandler, handler_type).__new__(handler_type)
    file_handler.set_data(data, config)
    return file_handler


def generate_files(
    args: MutableMapping[int, QuestionData],
    qid: int,
    title_slug: str,
    lc: QuestionDataClient,
    timestamp: float,
    config: AppConfig,
    code: str = "",
) -> None:
    """Auxiliar function to generate the question files

    Args:
         args (Dict[int, QuestionData]): a dictionary managed by the subprocess manager
         qid (int): the question id
         title_slug (str): the question title-slug property
         lc (LeetcodeClient): LeetcodeClient object
         timestamp (float): the time the question was generated
         config (AppConfig): the user config
         code (Optional[str], optional): the question solution. Defaults to "".
    """
    previous_signal_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        try:
            data = lc.get_question_data(qid, title_slug, config.language, code)
        except Exception as error:
            click.secho(str(error), fg="red")
            return

        data.language = config.language
        data.creation_time = timestamp
        try:
            file_handler = create_file_handler(data, config)
        except Exception as error:
            click.secho(f"Error: Could not prepare import for {qid}: {error}", fg="red")
            return

        test_limitation = get_local_test_limitation(data)
        if config.test_code.generate_tests and not test_limitation:
            if not data.inputs or not data.outputs:
                test_limitation = "LeetCode did not provide parseable input and output examples"
            elif len(data.inputs) != len(data.outputs):
                test_limitation = f"parsed {len(data.inputs)} inputs but {len(data.outputs)} outputs"

        try:
            data.function_name = file_handler.get_function_name()
        except Exception as error:
            if not test_limitation:
                test_limitation = f"could not identify the callable: {error}"

        if test_limitation:
            data.requires_custom_test_harness = True

        try:
            data.file_path = str(file_handler.generate_source())
        except Exception as error:
            click.secho(f"Error: Could not import source for {qid}: {error}", fg="red")
            return

        if config.test_code.generate_tests:
            if test_limitation:
                _report_soft_test_error(qid, data.title, test_limitation)
            else:
                try:
                    data.test_file_path = file_handler.generate_tests()
                except Exception as error:
                    data.requires_custom_test_harness = True
                    data.test_file_path = ""
                    try:
                        file_handler.remove_test_entrypoint()
                    except Exception as cleanup_error:
                        click.secho(
                            f"Could not remove the local test entrypoint: {cleanup_error}",
                            fg="yellow",
                        )
                    _remove_partial_test_file(data, config)
                    _report_soft_test_error(
                        qid,
                        data.title,
                        f"test generation failed: {type(error).__name__}: {error}",
                    )

        args[qid] = data
        click.secho(f"""The question "{qid}|{data.title}" was imported""")
    finally:
        signal.signal(signal.SIGINT, previous_signal_handler)


def _report_soft_test_error(qid: int, title: str, reason: str) -> None:
    """Report a non-fatal local-test limitation after preserving the source import."""
    click.secho(
        f'Soft error: imported source for "{qid}|{title}" without local tests: {reason}.',
        fg="yellow",
    )


def _remove_partial_test_file(data: QuestionData, config: AppConfig) -> None:
    """Remove a partially written Python test after non-fatal generation failure."""
    if data.language not in {"python", "python3"}:
        return
    test_path = Path(config.source_path, "tests", f"test_{data.id}.py")
    try:
        test_path.unlink(missing_ok=True)
    except OSError as error:
        click.secho(f"Could not remove incomplete test file {test_path}: {error}", fg="yellow")
