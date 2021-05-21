import os
import re
from typing import List

from autoimport import fix_files
from question_db import QuestionData


class PythonHandler:
    """Generates the source and test python files"""

    def __init__(self, question_data: QuestionData):
        self.question_data = question_data

    def generate_source(self):
        """Generates the source file"""
        with open(self.question_data.file_path, "a", encoding="UTF8") as f:
            f.write("        pass\n")

        # fix imports
        with open(self.question_data.file_path, "r+", encoding="UTF8") as f:
            fix_files([f])

        # add main
        with open(self.question_data.file_path, "a", encoding="UTF8") as f:
            f.write("\n")
            f.write("\n")
            f.write('if __name__ == "__main__":\n')
            f.write("    import pytest\n")
            f.write("    import os\n")
            f.write(
                f"    pytest.main([os.path.join('tests', 'test_{self.question_data.id}.py')])\n"
            )
            f.write("")

    def generete_tests(self):
        """Generates the test file"""
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
            f.write(
                f"    from src.{self.question_data.file_path[4:-3]} import Solution\n"
            )
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
                f.write(
                    f"    def test_solution_{i}(self, init_variables_{self.question_data.id}):\n"
                )
                f.write(
                    f"        assert"
                    + (" not" if self.question_data.outputs[i] == "false" else "")
                    + f" init_variables_{self.question_data.id}().{self.question_data.function_name}({self.question_data.inputs[i]})"
                    + (
                        f" == {self.question_data.outputs[i]}"
                        if self.question_data.outputs[i] not in ["true", "false"]
                        else ""
                    )
                    + "\n"
                )

    def generate_submission_file(self) -> str:
        lines: List[str] = []
        temporary_file: str = "tmp.py"
        # regex to match main definition
        match = r"""if\s+__name__\s+==\s+('|")__main__('|")\s*:\s*"""
        with open(self.question_data.file_path, "r", encoding="UTF8") as f:
            for line in f:
                if re.match(match, line):
                    break
                lines.append(line)

        with open(temporary_file, "w", encoding="UTF8") as f:
            f.writelines(lines)

        return temporary_file
