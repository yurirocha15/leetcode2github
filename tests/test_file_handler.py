from leet2git.config_manager import AppConfig
from leet2git.file_handler import generate_files
from leet2git.leetcode_client import LeetcodeAPIError
from leet2git.question_db import QuestionData


def test_generate_files_builds_source_and_tests(monkeypatch):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="Two Sum",
                title_slug=title_slug,
                file_path="src/leetcode_1_two_sum",
                language=language,
                inputs=["[2,7,11,15], 9"],
                outputs=["[0,1]"],
                raw_code=code,
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


def test_generate_files_skips_generic_tests_for_custom_output_metadata(monkeypatch, capsys):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="Remove Element",
                title_slug=title_slug,
                language=language,
                inputs=["[3,2,2,3], 3"],
                outputs=["2, nums = [2,2,_,_]"],
                requires_custom_test_harness=True,
            )

    class FakeHandler:
        def get_function_name(self):
            return ["removeElement"]

        def generate_source(self):
            return "src/leetcode_27_remove_element.py"

        def generate_tests(self):
            raise AssertionError("generic tests must not be generated")

    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: FakeHandler())
    generated = {}

    generate_files(generated, 27, "remove-element", FakeClient(), 123.0, AppConfig())

    assert generated[27].file_path == "src/leetcode_27_remove_element.py"
    assert generated[27].test_file_path == ""
    output = capsys.readouterr().out
    assert "Soft error" in output
    assert "custom or in-place output validation" in output


def test_generate_files_treats_judge_objects_as_soft_test_limitations(monkeypatch, capsys):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="Vertical Traversal",
                title_slug=title_slug,
                language=language,
                question_template="# class TreeNode:\n#     pass\nclass Solution:\n    pass\n",
                inputs=["[3,9,20]"],
                outputs=["[[9],[3],[20]]"],
            )

    class FakeHandler:
        def get_function_name(self):
            return ["verticalTraversal"]

        def generate_source(self):
            return "src/leetcode_987_vertical_traversal.py"

        def generate_tests(self):
            raise AssertionError("generic tests must not be generated")

    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: FakeHandler())
    generated = {}

    generate_files(generated, 987, "vertical-traversal", FakeClient(), 123.0, AppConfig())

    assert generated[987].file_path == "src/leetcode_987_vertical_traversal.py"
    assert generated[987].test_file_path == ""
    output = capsys.readouterr().out
    assert "Soft error" in output
    assert "TreeNode" in output


def test_generate_files_preserves_source_when_callable_discovery_fails(monkeypatch, capsys):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="Unusual Template",
                title_slug=title_slug,
                language=language,
                inputs=["1"],
                outputs=["1"],
            )

    class FakeHandler:
        def get_function_name(self):
            raise ValueError("no callable found")

        def generate_source(self):
            return "src/leetcode_999_unusual_template.py"

        def generate_tests(self):
            raise AssertionError("tests must be skipped without a callable")

    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: FakeHandler())
    generated = {}

    generate_files(generated, 999, "unusual-template", FakeClient(), 123.0, AppConfig())

    assert generated[999].file_path == "src/leetcode_999_unusual_template.py"
    assert generated[999].function_name == []
    assert "no callable found" in capsys.readouterr().out


def test_generate_files_cleans_partial_tests_after_soft_generation_error(tmp_path, monkeypatch, capsys):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="Broken Example",
                title_slug=title_slug,
                language=language,
                inputs=["1"],
                outputs=["1"],
            )

    class FakeHandler:
        entrypoint_removed = False

        def get_function_name(self):
            return ["solve"]

        def generate_source(self):
            return "src/leetcode_998_broken_example.py"

        def generate_tests(self):
            test_path = tmp_path / "tests" / "test_998.py"
            test_path.parent.mkdir(parents=True)
            test_path.write_text("invalid test", encoding="UTF8")
            raise SyntaxError("invalid generated assertion")

        def remove_test_entrypoint(self):
            self.entrypoint_removed = True

    handler = FakeHandler()
    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: handler)
    generated = {}
    config = AppConfig(source_path=str(tmp_path))

    generate_files(generated, 998, "broken-example", FakeClient(), 123.0, config)

    assert generated[998].file_path == "src/leetcode_998_broken_example.py"
    assert generated[998].test_file_path == ""
    assert handler.entrypoint_removed is True
    assert not (tmp_path / "tests" / "test_998.py").exists()
    assert "SyntaxError" in capsys.readouterr().out


def test_generate_files_contains_source_generation_failures(monkeypatch, capsys):
    class FakeClient:
        def get_question_data(self, qid, title_slug, language, code):
            return QuestionData(
                id=qid,
                title="No Source",
                title_slug=title_slug,
                language=language,
                inputs=["1"],
                outputs=["1"],
            )

    class FakeHandler:
        def get_function_name(self):
            return ["solve"]

        def generate_source(self):
            raise OSError("disk full")

    monkeypatch.setattr("leet2git.file_handler.create_file_handler", lambda *_: FakeHandler())
    generated = {}

    generate_files(generated, 997, "no-source", FakeClient(), 123.0, AppConfig())

    assert generated == {}
    assert "Could not import source" in capsys.readouterr().out
