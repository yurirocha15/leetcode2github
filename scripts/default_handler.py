import ast
import os
import re
from typing import List

from file_handler import FileHandler
from question_db import QuestionData


class DefaultHandler(FileHandler):
    """Generates the source files for languages without handlers"""

    languages = []

    def set_question_data(self, question_data: QuestionData):
        self.question_data = question_data

    def get_function_name(self) -> List[str]:
        """Returns the function name

        Returns:
            List[str]: a list with all function names
        """
        return list()

    def generate_source(self) -> str:
        """Generates the source file

        Returns:
            str: the path to the test file
        """
        comment: str = self.conversions[self.question_data.language]["comment"]
        extension: str = self.conversions[self.question_data.language]["extension"]
        lines: List[str] = (
            [
                comment + f"\n",
                comment + f" [{self.question_data.id}] {self.question_data.title}\n",
                comment + f" Difficulty: {self.question_data.difficulty}\n",
                comment + f" {self.question_data.url}\n",
                comment + f"\n",
            ]
            + [comment + " " + line + "\n" for line in self.question_data.description]
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
        lines.extend([l for l in code])
        self.question_data.file_path += extension

        with open(self.question_data.file_path, "w", encoding="UTF8") as f:
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
        with open(self.question_data.file_path, "r", encoding="UTF8") as f:
            for line in f:
                code += line

        return code
