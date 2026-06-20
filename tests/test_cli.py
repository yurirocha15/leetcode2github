from click.testing import CliRunner

from leet2git.config_manager import AppConfig
from leet2git.leet2git import leet2git
from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeAuthError
from leet2git.question_db import QuestionData


class FakeConfigManager:
    def __init__(self):
        self.config = AppConfig(language="python3", source_path="")

    def load_config(self, override_config=None):
        if override_config and override_config.source_path:
            self.config.source_path = override_config.source_path
        if override_config and override_config.language:
            self.config.language = override_config.language


class EmptyQuestionDB:
    def __init__(self, config):
        self.config = config

    def load(self):
        pass

    def check_if_exists(self, question_id):
        return False

    def check_if_slug_is_known(self, question_id):
        return False


def test_get_reports_auth_error_without_traceback(monkeypatch):
    class AuthFailClient:
        def __init__(self):
            raise LeetcodeAuthError("auth failed")

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", EmptyQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.LeetcodeClient", AuthFailClient)

    result = CliRunner().invoke(leet2git, ["get", "1"])

    assert result.exit_code == 0
    assert "auth failed" in result.output
    assert "Traceback" not in result.output


def test_submit_reports_api_error_without_traceback(monkeypatch):
    class SubmitQuestionDB(EmptyQuestionDB):
        def get_question(self, question_id):
            return QuestionData(id=question_id, internal_id=1, title_slug="two-sum")

    class FakeHandler:
        def generate_submission_file(self):
            return "class Solution: ..."

    class APIFailClient:
        def submit_question(self, *args, **kwargs):
            raise LeetcodeAPIError("api failed")

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", SubmitQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.create_file_handler", lambda *_: FakeHandler())
    monkeypatch.setattr("leet2git.leet2git.LeetcodeClient", APIFailClient)

    result = CliRunner().invoke(leet2git, ["submit", "1"])

    assert result.exit_code == 0
    assert "api failed" in result.output
    assert "Traceback" not in result.output


def test_delete_removes_files_from_configured_source_path(monkeypatch, tmp_path):
    source_file = tmp_path / "src" / "leetcode_1_two_sum.py"
    source_file.parent.mkdir()
    source_file.write_text("class Solution: ...\n", encoding="UTF8")

    class ConfigManagerWithSource(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

    class DeleteQuestionDB(EmptyQuestionDB):
        def __init__(self, config):
            super().__init__(config)
            self.deleted = False

        def check_if_exists(self, question_id):
            return True

        def get_data(self):
            return {
                1: QuestionData(
                    id=1,
                    file_path="src/leetcode_1_two_sum.py",
                    test_file_path="",
                )
            }

        def delete_question(self, question_id):
            self.deleted = True

        def save(self):
            pass

        def get_sorted_list(self, sort_by):
            return []

    class FakeReadmeHandler:
        def __init__(self, config):
            self.config = config

        def build_readme(self, question_list):
            pass

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ConfigManagerWithSource)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", DeleteQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.ReadmeHandler", FakeReadmeHandler)

    result = CliRunner().invoke(leet2git, ["delete", "1"])

    assert result.exit_code == 0
    assert not source_file.exists()
    assert "removed" in result.output
