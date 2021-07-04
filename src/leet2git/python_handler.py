import ast
import os
import re
import subprocess
import traceback
from typing import Any, Dict, List

import click
from autoimport import fix_files

from leet2git.file_handler import FileHandler
from leet2git.question_db import QuestionData


class PythonHandler(FileHandler):
    """Generates the source and test python files"""

    languages = ["python", "python3"]

    def set_data(self, question_data: QuestionData, config: Dict[str, Any]):
        """Sets the data needed to generate the files

        Args:
            question_data (QuestionData): the question data
            config (Dict[str, Any]): the app configuration
        """
        self.question_data = question_data
        self.config = config

    def get_function_name(self) -> List[str]:
        """Returns the function name

        Returns:
            List[str]: a list with all function names
        """
        functions: List[str] = re.findall(
            r"[^#\s*]\s+def\s+(.*?)\(self,", self.question_data.question_template
        )
        if functions[0] == "__init__":
            functions[0] = re.findall(r"^class\s+(.*?):", self.question_data.question_template)[0]
        self.question_data.function_name = functions
        return functions

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
        lines: List[str] = (
            [
                comment + f" @l2g {self.question_data.id} {self.question_data.language}\n",
                comment + f" [{self.question_data.id}] {self.question_data.title}\n",
                comment + f" Difficulty: {self.question_data.difficulty}\n",
                comment + f" {self.question_data.url}\n",
                comment + f"\n",
            ]
            + description
            + [
                "\n",
                "\n",
            ]
        )
        code, is_solution = (
            (self.question_data.raw_code, True)
            if self.question_data.raw_code
            else (self.question_data.question_template, False)
        )
        code_lines = self.parse_raw_code(code, is_solution)
        lines.extend([l for l in code_lines])
        self.question_data.file_path += extension

        full_path: str = os.path.join(self.config["source_path"], self.question_data.file_path)

        with open(full_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        # fix imports
        with open(full_path, "r+", encoding="UTF8") as f:
            try:
                fix_files([f])
            except Exception as e:
                click.secho(e.args, fg="red")
                click.secho(traceback.format_exc())

        # add main
        with open(full_path, "a", encoding="UTF8") as f:
            f.write("\n")
            f.write("\n")
            f.write('if __name__ == "__main__":\n')
            f.write("    import pytest\n")
            f.write("    import os\n")
            f.write(
                f"    pytest.main([os.path.join('tests', 'test_{self.question_data.id}{extension}')])\n"
            )
            f.write("")

        try:
            subprocess.run(
                f"isort --profile=black {full_path}",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
            )
            subprocess.run(
                f"black {full_path}", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True
            )
        except Exception as e:
            click.secho(e.args, fg="red")
            click.secho(traceback.format_exc())

        return self.question_data.file_path

    def generete_tests(self) -> str:
        """Generates the test file

        Returns:
            str: the path to the test file
        """
        extension: str = self.conversions[self.question_data.language]["extension"]
        self.question_data.inputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.inputs
        ]
        self.question_data.outputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.outputs
        ]
        inputs = self.question_data.inputs
        outputs = self.question_data.outputs
        if len(self.question_data.function_name) > 1:
            inputs = []
            outputs = []
            for input, output in zip(self.question_data.inputs, self.question_data.outputs):
                tmp_inputs = input.split(", ")
                inputs.append([])
                for tmp_input in tmp_inputs:
                    inputs[-1].append(ast.literal_eval(tmp_input))
                outputs.append(ast.literal_eval(output))
        elif not self.question_data.function_name:
            raise ValueError("No function name")
        full_path: str = os.path.join(
            self.config["source_path"], "tests", f"test_{self.question_data.id}{extension}"
        )
        with open(
            full_path,
            "a",
            encoding="UTF8",
        ) as f:
            f.write("#!/usr/bin/env python\n")
            f.write("\n")
            f.write("import pytest\n")
            f.write("\n")
            f.write("\n")
            f.write('"""\n')
            f.write(f"Test {self.question_data.id}. {self.question_data.title}\n")
            f.write('"""\n')
            f.write("\n")
            f.write("\n")
            f.write('@pytest.fixture(scope="session")\n')
            f.write(f"def init_variables_{self.question_data.id}():\n")
            if len(self.question_data.function_name) == 1:
                f.write(f"    from src.{self.question_data.file_path[4:-3]} import Solution\n")
                f.write(f"    solution = Solution()\n")
            else:
                try:
                    f.write(
                        f"    from src.{self.question_data.file_path[4:-3]} import {self.question_data.function_name[0]}\n"
                    )
                    f.write(
                        f"    solution = {self.question_data.function_name[0]}({str(inputs[0][1][0])[1:-1]})\n"
                    )
                except Exception as e:
                    print(e.args)
                    print(self.question_data)
            f.write("\n")
            f.write(f"    def _init_variables_{self.question_data.id}():\n")
            f.write("        return solution\n")
            f.write("\n")
            f.write(f"    yield _init_variables_{self.question_data.id}\n")
            f.write("\n")
            f.write(f"class TestClass{self.question_data.id}:")
            for i in range(len(inputs)):
                f.write("\n")
                f.write(f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n")
                if len(self.question_data.function_name) == 1:
                    f.write(
                        f"        assert"
                        + (" not" if outputs[i] == "False" else "")
                        + f" init_variables_{self.question_data.id}().{self.question_data.function_name[0]}({inputs[i]})"
                        + (f" == {outputs[i]}" if outputs[i] not in ["True", "False"] else "")
                        + "\n"
                    )
                else:
                    for input_func, input_val, output in zip(
                        inputs[i][0][1:], inputs[i][1][1:], outputs[i][1:]
                    ):
                        f.write(
                            f"        assert"
                            + (" not" if output == "False" else "")
                            + f" init_variables_{self.question_data.id}().{input_func}({str(input_val)[1:-1]})"
                            + (f" == {output}" if output not in ["True", "False"] else "")
                            + "\n"
                        )

        try:
            subprocess.run(
                f"isort --profile=black {full_path}",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
            )
            subprocess.run(
                f"black {full_path}", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True
            )
        except Exception as e:
            click.secho(e.args, fg="red")
            click.secho(traceback.format_exc())

        return os.path.join("tests", f"test_{self.question_data.id}{extension}")

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        code: str = ""
        # regex to match main definition
        match = r"""^if\s+__name__\s+==\s+('|")__main__('|")\s*:\s*"""
        full_path: str = os.path.join(self.config["source_path"], self.question_data.file_path)
        with open(full_path, "r", encoding="UTF8") as f:
            for line in f:
                if re.match(match, line):
                    break
                code += line

        return code

    def generate_repo(self, folder_path: str):
        """Generates a git repository

        Args:
            folder_path (str): the path to the repository folder
        """
        super().generate_repo(folder_path)
        os.makedirs(os.path.join(folder_path, "tests"), exist_ok=True)
        with open(os.path.join(folder_path, "src", "__init__.py"), "w") as file:
            file.write("\n")
        with open(os.path.join(folder_path, "tests", "__init__.py"), "w") as file:
            file.write("\n")

    def parse_raw_code(self, raw_code: str, is_solution: bool) -> List[str]:
        """Parses the raw code returned by leetcode

        Args:
            raw_code (str): the raw code returned by leetcode
            is_solution (bool): true if the raw_code is a solution

        Returns:
            List[str]: a list of lines of code
        """
        lines = []
        for i, line in enumerate(raw_code.split("\n")):
            lines.append(line + "\n")
            if re.match(r"^\s+def\s+(.*?)\(self,", line) and not is_solution:
                lines.append("        pass\n")

        return lines
