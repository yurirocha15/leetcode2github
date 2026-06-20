"""
File Handler for python language
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import ast
import io
import os
import shutil
import subprocess
import tokenize

import click
from autoimport import fix_files

from leet2git.config_manager import AppConfig
from leet2git.file_handler import FileHandler
from leet2git.question_db import QuestionData


class PythonHandler(FileHandler):
    """Generates the source and test python files"""

    languages: list[str] = ["python", "python3"]

    def __init__(self) -> None:
        super().__init__()
        self.question_data: QuestionData = QuestionData()
        self.config: AppConfig = AppConfig()

    def set_data(self, question_data: QuestionData, config: AppConfig):
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
        functions = self._get_template_callables(self.question_data.question_template)
        if not functions:
            raise ValueError("Could not find a Python function in the LeetCode code template.")
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
        code, is_solution = (
            (self.question_data.raw_code, True)
            if self.question_data.raw_code
            else (self.question_data.question_template, False)
        )
        code_lines = self.parse_raw_code(code, is_solution)
        lines.extend(code_lines)
        self.question_data.file_path += extension

        full_path: str = os.path.join(self.config.source_path, self.question_data.file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        # fix imports
        with open(full_path, "r+", encoding="UTF8") as f:
            fix_files((f,))

        if self.config.test_code.generate_tests:
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

        self.run_formatter(full_path)

        return self.question_data.file_path

    def generate_tests(self) -> str:
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
            for q_input, q_output in zip(
                self.question_data.inputs, self.question_data.outputs, strict=True
            ):
                tmp_inputs = q_input.split(", ")
                inputs.append([])
                for tmp_input in tmp_inputs:
                    inputs[-1].append(ast.literal_eval(tmp_input))
                outputs.append(ast.literal_eval(q_output))
        elif not self.question_data.function_name:
            raise ValueError("No function name")
        full_path: str = os.path.join(
            self.config.source_path, "tests", f"test_{self.question_data.id}{extension}"
        )
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
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
                f.write("    solution = Solution()\n")
            else:
                try:
                    f.write(
                        f"    from src.{self.question_data.file_path[4:-3]} \
                            import {self.question_data.function_name[0]}\n"
                    )
                    f.write(
                        f"    solution = {self.question_data.function_name[0]}\
                            ({str(inputs[0][1][0])[1:-1]})\n"
                    )
                # if we meet a question with some wild inputs
                except ValueError as e:
                    print(e.args)
                    print(self.question_data)
            f.write("\n")
            f.write(f"    def _init_variables_{self.question_data.id}():\n")
            f.write("        return solution\n")
            f.write("\n")
            f.write(f"    yield _init_variables_{self.question_data.id}\n")
            f.write("\n")
            f.write(f"class TestClass{self.question_data.id}:")
            for i, (q_input, q_output) in enumerate(zip(inputs, outputs, strict=True)):
                f.write("\n")
                f.write(f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n")
                if len(self.question_data.function_name) == 1:
                    f.write(
                        "        assert"
                        + (" not" if q_output == "False" else "")
                        + f" init_variables_{self.question_data.id}().\
                            {self.question_data.function_name[0]}({q_input})"
                        + (f" == {q_output}" if q_output not in ["True", "False"] else "")
                        + "\n"
                    )
                else:
                    for input_func, input_val, output in zip(
                        q_input[0][1:], q_input[1][1:], q_output[1:], strict=True
                    ):
                        f.write(
                            "        assert"
                            + (" not" if output == "False" else "")
                            + f" init_variables_{self.question_data.id}().\
                                {input_func}({str(input_val)[1:-1]})"
                            + (f" == {output}" if output not in ["True", "False"] else "")
                            + "\n"
                        )

        self.run_formatter(full_path)

        return os.path.join("tests", f"test_{self.question_data.id}{extension}")

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        full_path: str = os.path.join(self.config.source_path, self.question_data.file_path)
        with open(full_path, encoding="UTF8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        main_line = self._find_main_block_line(tree)
        if main_line is None:
            return source

        return "".join(source.splitlines(keepends=True)[: main_line - 1])

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

    def parse_raw_code(self, raw_code: str, is_solution: bool) -> list[str]:
        """Parses the raw code returned by leetcode

        Args:
            raw_code (str): the raw code returned by leetcode
            is_solution (bool): true if the raw_code is a solution

        Returns:
            List[str]: a list of lines of code
        """
        lines = []
        pass_after_lines = self._template_function_lines(raw_code) if not is_solution else set()
        for line_number, line in enumerate(raw_code.splitlines(), start=1):
            lines.append(line + "\n")
            if line_number in pass_after_lines:
                lines.append("        pass\n")
        if raw_code.endswith("\n"):
            lines.append("")

        return lines

    def _get_template_callables(self, source: str) -> list[str]:
        """Return callable names from a Python LeetCode template."""
        functions: list[str] = []
        class_stack: list[tuple[int, str]] = []
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.NAME and token.string == "class":
                class_token = next(tokens, None)
                if class_token and class_token.type == tokenize.NAME:
                    class_stack.append((token.start[1], class_token.string))
            elif token.type == tokenize.NAME and token.string == "def":
                function_token = next(tokens, None)
                if not function_token or function_token.type != tokenize.NAME:
                    continue
                if function_token.string == "__init__" and class_stack:
                    functions.append(class_stack[-1][1])
                else:
                    functions.append(function_token.string)

        return functions

    def _template_function_lines(self, source: str) -> set[int]:
        """Return template function line numbers that need placeholder bodies."""
        lines: set[int] = set()
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type != tokenize.NAME or token.string != "def":
                continue
            function_token = next(tokens, None)
            if function_token and function_token.type == tokenize.NAME:
                lines.add(token.start[0])
        return lines

    def _find_main_block_line(self, tree: ast.Module) -> int | None:
        """Return the line number of a generated __main__ block, if present."""
        for node in tree.body:
            if not isinstance(node, ast.If):
                continue
            compare = node.test
            if not isinstance(compare, ast.Compare):
                continue
            if not isinstance(compare.left, ast.Name) or compare.left.id != "__name__":
                continue
            if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
                continue
            if len(compare.comparators) != 1:
                continue
            comparator = compare.comparators[0]
            if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                return node.lineno
        return None

    def run_formatter(self, file_path: str) -> None:
        """Run Ruff formatter if it is available.

        Args:
            file_path (str): the path to the file
        """
        if not shutil.which("ruff"):
            click.secho(f"Skipping formatting for {file_path}: ruff is not installed.", fg="yellow")
            return
        try:
            subprocess.run(
                ["ruff", "check", "--fix", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            subprocess.run(
                ["ruff", "format", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            click.secho(f"Could not format {file_path}: {e}", fg="red")
