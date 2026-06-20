from leet2git.config_manager import AppConfig
from leet2git.file_handler import generate_files
from leet2git.leetcode_client import LeetcodeAPIError
from leet2git.question_db import QuestionData


def test_generate_files_builds_source_and_tests(monkeypatch):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return (
                QuestionData(
                    id=qid,
                    title="Two Sum",
                    title_slug=title_slug,
                    file_path="src/leetcode_1_two_sum",
                    language=language,
                    inputs=["[2,7,11,15], 9"],
                    outputs=["[0,1]"],
                    raw_code=code,
                ),
                True,
            )

    class FakeHandler:
        def get_function_name(self):
            return ["twoSum"]

        def generate_source(self):
            return "src/leetcode_1_two_sum.py"

        def generate_tests(self):
            return "tests/test_1.py"

    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: FakeHandler())

    generated = {}
    generate_files(generated, 1, "two-sum", FakeClient(), 123.0, AppConfig(), "solution code")

    assert generated[1].creation_time == 123.0
    assert generated[1].file_path == "src/leetcode_1_two_sum.py"
    assert generated[1].test_file_path == "tests/test_1.py"
    assert generated[1].function_name == ["twoSum"]
    assert generated[1].raw_code == "solution code"


def test_generate_files_reports_leetcode_errors(capsys):
    class FakeClient:
        def get_question_data(self, *args):
            raise LeetcodeAPIError("api changed")

    generated = {}
    generate_files(generated, 1, "two-sum", FakeClient(), 123.0, AppConfig())

    assert generated == {}
    assert "api changed" in capsys.readouterr().out
