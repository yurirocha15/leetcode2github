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
from pathlib import Path

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

    def get_function_name(self) -> list[str]:
        """Returns the function name

        Returns:
            List[str]: a list with all function names
        """
        functions = self._get_template_callables(self.question_data.question_template)
        if not functions:
            raise ValueError("Could not find a Python function in the LeetCode code template.")
        return functions

    def generate_source(self) -> Path:
        """Generates the source file

        Returns:
            Path: the path to the generated source file
        """
        comment, extension, lines = self._build_source_header()
        code, is_solution = (
            (self.question_data.raw_code, True)
            if self.question_data.raw_code
            else (self.question_data.question_template, False)
        )
        code_lines = self.parse_raw_code(code, is_solution)
        if self.question_data.language == "python3":
            code_lines = self._ensure_future_annotations(code_lines)
        lines.extend(code_lines)
        file_path = self.question_data.file_path + extension

        full_path: str = os.path.join(self.config.source_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        # fix imports
        with open(full_path, "r+", encoding="UTF8") as f:
            fix_files((f,))

        if self.config.test_code.generate_tests and not self.question_data.requires_custom_test_harness:
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

        return Path(file_path)

    def remove_test_entrypoint(self) -> None:
        """Remove the generated pytest launcher after local test generation fails."""
        full_path = os.path.join(self.config.source_path, self.question_data.file_path)
        try:
            with open(full_path, encoding="UTF8") as file:
                source = file.read()
            tree = ast.parse(source)
            main_line = self._find_main_block_line(tree)
            if main_line is None:
                return
            with open(full_path, "w", encoding="UTF8") as file:
                file.write("".join(source.splitlines(keepends=True)[: main_line - 1]))
        except (OSError, SyntaxError) as error:
            click.secho(f"Could not remove the local test entrypoint: {error}", fg="yellow")

    def generate_tests(self) -> str:
        """Generates the test file

        Returns:
            str: the path to the test file
        """
        from leet2git.file_handler import LANGUAGE_CONVERSIONS

        extension: str = LANGUAGE_CONVERSIONS[self.question_data.language]["extension"]
        inputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.inputs
        ]
        outputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.outputs
        ]
        design_cases: list[tuple[list[str], list[list[object]], list[object]]] = []
        if len(self.question_data.function_name) > 1:
            for q_input, q_output in zip(inputs, outputs, strict=True):
                design_cases.append(self._parse_design_case(q_input, q_output))
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
                f.write("\n")
                f.write(f"    def _init_variables_{self.question_data.id}():\n")
                f.write("        return solution\n")
            else:
                constructor = self.question_data.function_name[0]
                f.write(f"    from src.{self.question_data.file_path[4:-3]} import {constructor}\n")
                f.write("\n")
                f.write(f"    def _init_variables_{self.question_data.id}(*args):\n")
                f.write(f"        return {constructor}(*args)\n")
            f.write("\n")
            f.write(f"    yield _init_variables_{self.question_data.id}\n")
            f.write("\n")
            f.write(f"class TestClass{self.question_data.id}:")
            if len(self.question_data.function_name) == 1:
                for i, (q_input, q_output) in enumerate(zip(inputs, outputs, strict=True)):
                    f.write("\n")
                    f.write(
                        f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n"
                    )
                    f.write(
                        "        assert"
                        + (" not" if q_output == "False" else "")
                        + f" init_variables_{self.question_data.id}().\
                            {self.question_data.function_name[0]}({q_input})"
                        + (f" == {q_output}" if q_output not in ["True", "False"] else "")
                        + "\n"
                    )
            else:
                for i, (method_names, method_inputs, expected_outputs) in enumerate(design_cases):
                    f.write("\n")
                    f.write(
                        f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n"
                    )
                    constructor_args = ", ".join(repr(value) for value in method_inputs[0])
                    f.write(
                        f"        solution = init_variables_{self.question_data.id}"
                        f"({constructor_args})\n"
                    )
                    for input_func, input_val, output in zip(
                        method_names[1:],
                        method_inputs[1:],
                        expected_outputs[1:],
                        strict=True,
                    ):
                        arguments = ", ".join(repr(value) for value in input_val)
                        call = f"solution.{input_func}({arguments})"
                        f.write("        " + self._build_assertion(call, output) + "\n")

        self.run_formatter(full_path)

        return os.path.join("tests", f"test_{self.question_data.id}{extension}")

    def _parse_design_case(
        self, raw_input: str, raw_output: str
    ) -> tuple[list[str], list[list[object]], list[object]]:
        """Parse one LeetCode design-problem example into methods, arguments, and outputs."""
        try:
            parsed_input = ast.literal_eval(f"({raw_input})")
            parsed_output = ast.literal_eval(raw_output)
        except (SyntaxError, ValueError) as e:
            raise ValueError("Could not parse the design-problem example data.") from e

        if not isinstance(parsed_input, tuple) or len(parsed_input) != 2:
            raise ValueError("Design-problem input must contain method and argument lists.")
        method_names, method_inputs = parsed_input
        if (
            not isinstance(method_names, list)
            or not all(isinstance(name, str) for name in method_names)
            or not isinstance(method_inputs, list)
            or not all(isinstance(arguments, list) for arguments in method_inputs)
            or not isinstance(parsed_output, list)
        ):
            raise ValueError("Design-problem example data has an unexpected shape.")
        if not method_names or not (len(method_names) == len(method_inputs) == len(parsed_output)):
            raise ValueError("Design-problem method, argument, and output counts must match.")

        return method_names, method_inputs, parsed_output

    @staticmethod
    def _build_assertion(call: str, expected: object) -> str:
        """Build a valid pytest assertion for a generated design-problem method call."""
        if expected is True:
            return f"assert {call}"
        if expected is False:
            return f"assert not {call}"
        if expected is None:
            return f"assert {call} is None"
        return f"assert {call} == {expected!r}"

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        full_path = os.path.join(self.config.source_path, self.question_data.file_path)
        try:
            with open(full_path, encoding="UTF8") as f:
                source = f.read()
        except OSError as e:
            raise click.ClickException(f"Failed to read source file: {e}") from e

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        main_line = self._find_main_block_line(tree)
        if main_line is None:
            return source

        return "".join(source.splitlines(keepends=True)[: main_line - 1])

    def generate_repo(self, folder_path: str) -> None:
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

    @staticmethod
    def _ensure_future_annotations(code_lines: list[str]) -> list[str]:
        """Defer Python 3 annotations while preserving docstrings and existing future imports."""
        try:
            tree = ast.parse("".join(code_lines))
        except SyntaxError:
            return code_lines

        if any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(name.name == "annotations" for name in node.names)
            for node in tree.body
        ):
            return code_lines

        insertion_line = 0
        body_index = 0
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            insertion_line = tree.body[0].end_lineno or tree.body[0].lineno
            body_index = 1

        for node in tree.body[body_index:]:
            if not isinstance(node, ast.ImportFrom) or node.module != "__future__":
                break
            insertion_line = node.end_lineno or node.lineno

        future_lines = ["from __future__ import annotations\n"]
        if insertion_line >= len(code_lines) or code_lines[insertion_line].strip():
            future_lines.append("\n")
        return code_lines[:insertion_line] + future_lines + code_lines[insertion_line:]

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
                ["ruff", "check", "--fix", "--select", "I,UP,F401", file_path],
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
