import ast
import runpy

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


def test_generate_source_adds_test_entrypoint_when_enabled(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Two Sum",
        difficulty="Easy",
        url="https://leetcode.com/problems/two-sum",
        file_path="src/leetcode_1_two_sum",
        language="python3",
        question_template="class Solution:\n    def twoSum(self, nums, target):\n",
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    file_path = handler.generate_source()

    content = (tmp_path / file_path).read_text(encoding="UTF8")
    assert 'if __name__ == "__main__"' in content
    assert "pytest.main([os.path.join('tests', 'test_1.py')])" in content


def test_generate_source_omits_test_entrypoint_for_soft_error_import(tmp_path, monkeypatch):
    question = QuestionData(
        id=987,
        title="Vertical Traversal",
        file_path="src/leetcode_987_vertical_traversal",
        language="python3",
        question_template=(
            "# class TreeNode:\n"
            "#     pass\n"
            "class Solution:\n"
            "    def verticalTraversal(self, root: TreeNode | None):\n"
        ),
        requires_custom_test_harness=True,
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    file_path = handler.generate_source()

    content = (tmp_path / file_path).read_text(encoding="UTF8")
    assert "class Solution" in content
    assert 'if __name__ == "__main__"' not in content


def test_remove_test_entrypoint_preserves_generated_solution(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Two Sum",
        file_path="src/leetcode_1_two_sum",
        language="python3",
        question_template="class Solution:\n    def twoSum(self, nums, target):\n",
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)
    question.file_path = str(handler.generate_source())

    handler.remove_test_entrypoint()

    content = (tmp_path / question.file_path).read_text(encoding="UTF8")
    assert "class Solution" in content
    assert 'if __name__ == "__main__"' not in content


@pytest.mark.parametrize("judge_type", ["TreeNode", "ListNode"])
def test_generate_source_defers_judge_type_annotations(judge_type, tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Judge Type",
        file_path="src/leetcode_1_judge_type",
        language="python3",
        question_template=(
            f"# class {judge_type}:\n"
            "#     pass\n"
            "class Solution:\n"
            f"    def visit(self, node: {judge_type} | None) -> {judge_type} | None:\n"
        ),
    )
    handler = make_handler(
        question,
        AppConfig(
            source_path=str(tmp_path),
            test_code=LeetTestCodeConfig(generate_tests=False),
        ),
    )
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    source_path = tmp_path / handler.generate_source()
    content = source_path.read_text(encoding="UTF8")

    assert content.count("from __future__ import annotations") == 1
    namespace = runpy.run_path(str(source_path), run_name="generated_solution")
    assert "Solution" in namespace


def test_generate_source_keeps_module_docstring_before_future_import(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Documented",
        file_path="src/leetcode_1_documented",
        language="python3",
        question_template=(
            '"""Starter module documentation."""\n\nclass Solution:\n    def solve(self):\n'
        ),
    )
    handler = make_handler(
        question,
        AppConfig(
            source_path=str(tmp_path),
            test_code=LeetTestCodeConfig(generate_tests=False),
        ),
    )
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    source_path = tmp_path / handler.generate_source()
    content = source_path.read_text(encoding="UTF8")

    assert content.index('"""Starter module documentation."""') < content.index(
        "from __future__ import annotations"
    )
    namespace = runpy.run_path(str(source_path), run_name="generated_solution")
    assert namespace["__doc__"] == "Starter module documentation."


def test_generate_source_does_not_duplicate_existing_annotations_future(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Future",
        file_path="src/leetcode_1_future",
        language="python3",
        raw_code=("from __future__ import annotations\n\nclass Solution:\n    pass\n"),
    )
    handler = make_handler(
        question,
        AppConfig(
            source_path=str(tmp_path),
            test_code=LeetTestCodeConfig(generate_tests=False),
        ),
    )
    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    source_path = tmp_path / handler.generate_source()

    assert source_path.read_text(encoding="UTF8").count("from __future__ import annotations") == 1


def test_generate_tests_creates_single_function_pytest_file(tmp_path, monkeypatch):
    question = QuestionData(
        id=1,
        title="Two Sum",
        file_path="src/leetcode_1_two_sum.py",
        language="python3",
        function_name=["twoSum"],
        inputs=["[2,7,11,15], 9", "[3,2,4], 6"],
        outputs=["[0, 1]", "[1, 2]"],
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    test_file_path = handler.generate_tests()

    content = (tmp_path / test_file_path).read_text(encoding="UTF8")
    assert test_file_path == "tests/test_1.py"
    assert "from src.leetcode_1_two_sum import Solution" in content
    assert "twoSum([2,7,11,15], 9) == [0, 1]" in content
    assert "twoSum([3,2,4], 6) == [1, 2]" in content


def test_generate_tests_creates_constructor_style_pytest_file(tmp_path, monkeypatch):
    question = QuestionData(
        id=2013,
        title="Detect Squares",
        file_path="src/leetcode_2013_detect_squares.py",
        language="python3",
        question_template=(
            "class DetectSquares:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def add(self, point):\n"
            "        pass\n"
            "    def count(self, point):\n"
            "        pass\n"
        ),
        inputs=[
            '["DetectSquares","add","add","add","count","count","add","count"], '
            "[[],[[3,10]],[[11,2]],[[3,2]],[[11,10]],[[14,8]],[[11,2]],[[11,10]]]"
        ],
        outputs=["[null,null,null,null,1,0,null,2]"],
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    question.function_name = handler.get_function_name()
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    test_file_path = handler.generate_tests()

    content = (tmp_path / test_file_path).read_text(encoding="UTF8")
    assert question.function_name == ["DetectSquares", "add", "count"]
    assert "from src.leetcode_2013_detect_squares import DetectSquares" in content
    assert "return DetectSquares(*args)" in content
    assert "solution = init_variables_2013()" in content
    assert "solution = add()" not in content
    assert "add([3, 10]) is None" in content
    assert "count([11, 10]) == 1" in content
    assert "count([11, 10]) == 2" in content
    ast.parse(content)


def test_generate_tests_uses_each_design_cases_constructor_arguments(tmp_path, monkeypatch):
    question = QuestionData(
        id=1000,
        title="Accumulator",
        file_path="src/leetcode_1000_accumulator.py",
        language="python3",
        function_name=["Accumulator", "add"],
        inputs=[
            '["Accumulator","add"], [[1],[2]]',
            '["Accumulator","add"], [[10],[2]]',
        ],
        outputs=["[null,3]", "[null,12]"],
    )
    handler = make_handler(question, AppConfig(source_path=str(tmp_path)))
    monkeypatch.setattr(handler, "run_formatter", lambda _: None)

    test_file_path = handler.generate_tests()

    content = (tmp_path / test_file_path).read_text(encoding="UTF8")
    assert "solution = init_variables_1000(1)" in content
    assert "solution = init_variables_1000(10)" in content
    assert "solution.add(2) == 3" in content
    assert "solution.add(2) == 12" in content
    ast.parse(content)


def test_generate_tests_requires_function_name(tmp_path):
    handler = make_handler(
        QuestionData(
            id=1,
            file_path="src/leetcode_1_two_sum.py",
            language="python3",
            inputs=["[2,7,11,15], 9"],
            outputs=["[0, 1]"],
        ),
        AppConfig(source_path=str(tmp_path)),
    )

    with pytest.raises(ValueError, match="No function name"):
        handler.generate_tests()


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

    assert calls[0][0] == ["ruff", "check", "--fix", "--select", "I,UP,F401", "solution.py"]
    assert calls[1][0] == ["ruff", "format", "solution.py"]
    assert all("shell" not in kwargs for _, kwargs in calls)
