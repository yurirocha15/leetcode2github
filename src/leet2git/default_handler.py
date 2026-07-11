"""
File Handler for languages without a specific handler
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import os
from pathlib import Path

import click

from leet2git.config_manager import AppConfig
from leet2git.file_handler import FileHandler
from leet2git.question_db import QuestionData


class DefaultHandler(FileHandler):
    """Generates the source files for languages without handlers"""

    languages: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self.question_data: QuestionData = QuestionData()
        self.config: AppConfig = AppConfig()

    def get_function_name(self) -> list[str]:
        """Returns the function name

        Returns:
            List[str]: a list with all function names
        """
        return []

    def generate_source(self) -> Path:
        """Generates the source file

        Returns:
            Path: the path to the generated source file
        """
        comment, extension, lines = self._build_source_header()
        code = (
            self.question_data.raw_code
            if self.question_data.raw_code
            else self.question_data.question_template
        )
        lines.append(code)
        file_path = self.question_data.file_path + extension
        full_path = os.path.join(self.config.source_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        return Path(file_path)

    def generate_tests(self) -> str:
        """Not Implemented"""
        return ""

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        file_path = os.path.join(self.config.source_path, self.question_data.file_path)
        try:
            with open(file_path, encoding="UTF8") as f:
                return f.read()
        except OSError as e:
            raise click.ClickException(f"Failed to read source file: {e}") from e
