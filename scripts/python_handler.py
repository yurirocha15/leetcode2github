import os
import re
from typing import List

from autoimport import fix_files
from file_handler import FileHandler
from question_db import QuestionData


class PythonHandler(FileHandler):
    """Generates the source and test python files"""

    languages = ["python", "python3"]

    def set_question_data(self, question_data: QuestionData):
        self.question_data = question_data

    def get_function_name(self) -> str:
        """Returns the function name

        Returns:
            str: the function name
        """
        code = (
            self.question_data.raw_code
            if self.question_data.raw_code
            else self.question_data.question_template
        )
        return re.findall(r"    def (.*?)\(self,", code)[0]

    def generate_source(self) -> str:
        """Generates the source file

        Returns:
            str: the path to the test file
        """
        lines: List[str] = (
            [
                f"#\n",
                f"# [{self.question_data.id}] {self.question_data.title}\n",
                f"# Difficulty: {self.question_data.difficulty}\n",
                f"# {self.question_data.url}\n",
                f"#\n",
            ]
            + ["# " + line + "\n" for line in self.question_data.description]
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
        self.question_data.file_path += ".py"

        with open(self.question_data.file_path, "w", encoding="UTF8") as f:
            f.writelines(lines)

        # fix imports
        with open(self.question_data.file_path, "r+", encoding="UTF8") as f:
            try:
                fix_files([f])
            except Exception as e:
                print(e.args)

        # add main
        with open(self.question_data.file_path, "a", encoding="UTF8") as f:
            f.write("\n")
            f.write("\n")
            f.write('if __name__ == "__main__":\n')
            f.write("    import pytest\n")
            f.write("    import os\n")
            f.write(f"    pytest.main([os.path.join('tests', 'test_{self.question_data.id}.py')])\n")
            f.write("")

        return self.question_data.file_path

    def generete_tests(self) -> str:
        """Generates the test file

        Returns:
            str: the path to the test file
        """
        self.question_data.inputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.inputs
        ]
        self.question_data.outputs = [
            s.replace("null", "None").replace("true", "True").replace("false", "False")
            for s in self.question_data.outputs
        ]
        with open(
            os.path.join("tests", f"test_{self.question_data.id}.py"),
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
            f.write(f"    from src.{self.question_data.file_path[4:-3]} import Solution\n")
            f.write(f"    solution = Solution()\n")
            f.write("\n")
            f.write(f"    def _init_variables_{self.question_data.id}():\n")
            f.write("        return solution\n")
            f.write("\n")
            f.write(f"    yield _init_variables_{self.question_data.id}\n")
            f.write("\n")
            f.write(f"class TestClass{self.question_data.id}:")
            for i in range(len(self.question_data.inputs)):
                f.write("\n")
                f.write(f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n")
                f.write(
                    f"        assert"
                    + (" not" if self.question_data.outputs[i] == "False" else "")
                    + f" init_variables_{self.question_data.id}().{self.question_data.function_name}({self.question_data.inputs[i]})"
                    + (
                        f" == {self.question_data.outputs[i]}"
                        if self.question_data.outputs[i] not in ["True", "False"]
                        else ""
                    )
                    + "\n"
                )
        return os.path.join("tests", f"test_{self.question_data.id}.py")

    def generate_submission_file(self) -> str:
        """Generates the submission file

        Returns:
            str: a string containing the code
        """
        code: str = ""
        # regex to match main definition
        match = r"""if\s+__name__\s+==\s+('|")__main__('|")\s*:\s*"""
        with open(self.question_data.file_path, "r", encoding="UTF8") as f:
            for line in f:
                if re.match(match, line):
                    break
                code += line

        return code

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
            if re.match(r"    def (.*?)\(self,", line) and not is_solution:
                lines.append("        pass\n")

        return lines
