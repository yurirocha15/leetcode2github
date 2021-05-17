import os

from autoimport import fix_files
from question_db import QuestionData


class PythonHandler:
    """Generates the source and test python files"""

    def __init__(self, question_data: QuestionData):
        self.question_data = question_data

    def generate_source(self):
        """Generates the source file"""
        with open(self.question_data.file_path, "a") as f:
            f.write("        pass\n")
            f.write("\n")
            f.write("\n")
            f.write('if __name__ == "__main__":\n')
            f.write("    import pytest\n")
            f.write(
                f"    pytest.main(['{os.path.join('tests', f'test_{self.question_data.id}.py')}'])\n"
            )
            f.write("")

        with open(self.question_data.file_path, "r+") as f:
            fix_files([f])

    def generete_tests(self):
        """Generates the test file"""
        with open(os.path.join("tests", f"test_{self.question_data.id}.py"), "a") as f:
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
