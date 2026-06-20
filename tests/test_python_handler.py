import pytest

from leet2git.config_manager import AppConfig
from leet2git.config_manager import TestCodeConfig as LeetTestCodeConfig
from leet2git.file_handler import create_file_handler
from leet2git.python_handler import PythonHandler
from leet2git.question_db import QuestionData


def make_handler(
    question_data: QuestionData | None = None,
    config: AppConfig | None = None,
) -> PythonHandler:
    handler = PythonHandler()
    handler.set_data(
        question_data or QuestionData(question_template="class Solution:\n    def twoSum(self):\n"),
        config or AppConfig(),
    )
    return handler


def test_python_handler_imports_without_file_handler_side_effect():
    handler = PythonHandler()

    assert handler.languages == ["python", "python3"]


def test_create_file_handler_uses_lazy_registry():
    handler = create_file_handler(QuestionData(language="python3"), AppConfig(language="python3"))
    fallback = create_file_handler(QuestionData(language="rust"), AppConfig(language="rust"))

    assert type(handler).__name__ == "PythonHandler"
    assert type(fallback).__name__ == "DefaultHandler"


def test_get_function_name_requires_function_template():
    handler = make_handler(QuestionData(question_template="class Solution:\n    pass\n"))

    with pytest.raises(ValueError, match="function"):
        handler.get_function_name()


def test_get_function_name_supports_constructor_style_template():
    handler = make_handler(
        QuestionData(question_template="class LRUCache:\n    def __init__(self, capacity: int):\n")
    )

    assert handler.get_function_name() == ["LRUCache"]


def test_generate_source_creates_python_file_without_tests_when_disabled(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Two Sum",
        difficulty="Easy",
        url="https://leetcode.com/problems/two-sum",
        file_path="src/leetcode_1_two_sum",
        language="python3",
        question_template="class Solution:\n    def twoSum(self, nums, target):\n",
    )
    config = AppConfig(
        source_path=str(tmp_path),
        test_code=LeetTestCodeConfig(generate_tests=False),
    )
    handler = make_handler(question, config)
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    file_path = handler.generate_source()

    generated = tmp_path / file_path
    assert generated.exists()
    content = generated.read_text(encoding="UTF8")
    assert "def twoSum" in content
    assert "        pass" in content
    assert 'if __name__ == "__main__"' not in content


def test_generate_submission_file_strips_generated_main_block(tmp_path):
    question = QuestionData(file_path="src/leetcode_1_two_sum.py")
    full_path = tmp_path / question.file_path
    full_path.parent.mkdir()
    full_path.write_text(
        "class Solution:\n    pass\n\nif __name__ == \"__main__\":\n    print('run')\n",
        encoding="UTF8",
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))

    assert handler.generate_submission_file() == "class Solution:\n    pass\n\n"


def test_run_formatter_skips_when_ruff_is_unavailable(monkeypatch, capsys):
    handler = make_handler()
    monkeypatch.setattr("leet2git.python_handler.shutil.which", lambda _: None)

    handler.run_formatter("solution.py")

    assert "ruff is not installed" in capsys.readouterr().out


def test_run_formatter_invokes_ruff_without_shell(monkeypatch):
    handler = make_handler()
    calls = []
    monkeypatch.setattr("leet2git.python_handler.shutil.which", lambda _: "/usr/bin/ruff")
    monkeypatch.setattr(
        "leet2git.python_handler.subprocess.run",
        lambda args, **kwargs: calls.append((args, kwargs)),
    )

    handler.run_formatter("solution.py")

    assert calls[0][0] == ["ruff", "check", "--fix", "solution.py"]
    assert calls[1][0] == ["ruff", "format", "solution.py"]
    assert all("shell" not in kwargs for _, kwargs in calls)
