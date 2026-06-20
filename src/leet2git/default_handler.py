"""
File Handler for languages without a specific handler
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import os
from typing import Any

from leet2git.file_handler import FileHandler
from leet2git.question_db import QuestionData


class DefaultHandler(FileHandler):
    """Generates the source files for languages without handlers"""

    languages: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self.question_data: QuestionData = QuestionData()
        self.config: dict[str, Any] = {}

    def set_data(self, question_data: QuestionData, config: dict[str, Any]):
        """Sets the data needed to generate the files

        Args:
            question_data (QuestionData): the question data
            config (Dict[str, Any]): the app configuration
        """
        self.question_data = question_data
        self.config = config

    def get_function_name(self) -> list[str]:
        """Returns the function name

        Returns:
            List[str]: a list with all function names
        """
        return []

    def generate_source(self) -> str:
        """Generates the source file

        Returns:
            str: the path to the test file
        """
        comment: str = self.conversions[self.question_data.language]["comment"]
        extension: str = self.conversions[self.question_data.language]["extension"]
        description = (
            [comment + " " + line + "\n" for line in self.question_data.description]
            if self.config["source_code"]["add_description"]
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
        code = (
            self.question_data.raw_code
            if self.question_data.raw_code
            else self.question_data.question_template
        )
        lines.extend(code)
        self.question_data.file_path += extension
        full_path = os.path.join(self.config["source_path"], self.question_data.file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        return self.question_data.file_path

    def generete_tests(self) -> str:
        """Not Implemented"""
        return ""

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        code: str = ""
        with open(
            os.path.join(self.config["source_path"], self.question_data.file_path), encoding="UTF8"
        ) as f:
            for line in f:
                code += line

        return code
