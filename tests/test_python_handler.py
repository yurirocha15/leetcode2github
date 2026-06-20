import pytest

import leet2git.file_handler  # noqa: F401
from leet2git.python_handler import PythonHandler
from leet2git.question_db import QuestionData


def make_handler(question_data: QuestionData | None = None) -> PythonHandler:
    handler = PythonHandler()
    handler.set_data(
        question_data or QuestionData(question_template="class Solution:\n    def twoSum(self):\n"),
        {
            "source_path": "",
            "source_code": {"add_description": True},
            "test_code": {"generate_tests": True},
        },
    )
    return handler


def test_get_function_name_requires_function_template():
    handler = make_handler(QuestionData(question_template="class Solution:\n    pass\n"))

    with pytest.raises(ValueError, match="function"):
        handler.get_function_name()


def test_run_formatter_skips_when_ruff_is_unavailable(monkeypatch, capsys):
    handler = make_handler()
    monkeypatch.setattr("leet2git.python_handler.shutil.which", lambda _: None)

    handler.run_formatter("solution.py")

    assert "ruff is not installed" in capsys.readouterr().out
