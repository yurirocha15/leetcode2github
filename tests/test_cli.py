from click.testing import CliRunner

from leet2git.config_manager import AppConfig
from leet2git.leet2git import leet2git
from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeAuthError
from leet2git.leetcode_models import SubmissionListResponse
from leet2git.question_db import IdTitleMap, QuestionData


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


def test_get_skips_existing_question(monkeypatch):
    class ExistingQuestionDB(EmptyQuestionDB):
        def check_if_exists(self, question_id):
            return True

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", ExistingQuestionDB)

    result = CliRunner().invoke(leet2git, ["get", "1"])

    assert result.exit_code == 0
    assert "Question already imported" in result.output


def test_get_imports_question_and_updates_readme(monkeypatch, tmp_path):
    class ConfigManagerWithSource(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

    class ImportOneQuestionDB(EmptyQuestionDB):
        instances = []

        def __init__(self, config):
            super().__init__(config)
            self.questions = {}
            self.id_title_map = IdTitleMap()
            self.save_count = 0
            self.instances.append(self)

        def check_if_exists(self, question_id):
            return question_id in self.questions

        def check_if_slug_is_known(self, question_id):
            return question_id in self.id_title_map.id_to_title

        def set_id_title_map(self, id_title_map):
            self.id_title_map = id_title_map

        def get_title_from_id(self, question_id):
            return self.id_title_map.id_to_title[question_id]

        def add_question(self, question):
            self.questions[question.id] = question

        def save(self):
            self.save_count += 1

        def get_sorted_list(self, sort_by):
            return sorted(self.questions.values(), key=lambda question: question.creation_time)

    class FakeClient:
        def get_id_title_map(self):
            return IdTitleMap(id_to_title={1: "two-sum"}, title_to_id={"two-sum": 1})

    class FakeReadmeHandler:
        built_lists = []

        def __init__(self, config):
            self.config = config

        def build_readme(self, question_list):
            self.built_lists.append(question_list)

    def fake_generate_files(args, question_id, title_slug, lc, timestamp, config, code=""):
        args[question_id] = QuestionData(
            id=question_id,
            title="Two Sum",
            title_slug=title_slug,
            creation_time=timestamp,
        )

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ConfigManagerWithSource)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", ImportOneQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.LeetcodeClient", FakeClient)
    monkeypatch.setattr("leet2git.leet2git.ReadmeHandler", FakeReadmeHandler)
    monkeypatch.setattr("leet2git.leet2git.generate_files", fake_generate_files)

    result = CliRunner().invoke(leet2git, ["get", "1"])

    imported_db = ImportOneQuestionDB.instances[-1]
    assert result.exit_code == 0
    assert imported_db.questions[1].title == "Two Sum"
    assert imported_db.save_count == 2
    assert [question.id for question in FakeReadmeHandler.built_lists[-1]] == [1]


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


def test_submit_reports_missing_question(monkeypatch):
    class SubmitQuestionDB(EmptyQuestionDB):
        def get_question(self, question_id):
            return None

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", SubmitQuestionDB)

    result = CliRunner().invoke(leet2git, ["submit", "1"])

    assert result.exit_code == 0
    assert "Could not find the question with id 1" in result.output


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


def test_delete_reports_missing_question(monkeypatch):
    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", EmptyQuestionDB)

    result = CliRunner().invoke(leet2git, ["delete", "1"])

    assert result.exit_code == 0
    assert "could not be found" in result.output


def test_run_submits_generated_code_with_question_inputs(monkeypatch, tmp_path):
    class ConfigManagerWithSource(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

    class RunQuestionDB(EmptyQuestionDB):
        def get_question(self, question_id):
            return QuestionData(
                id=question_id,
                internal_id=1,
                inputs=["[2,7,11,15], 9", "[3,2,4], 6"],
            )

        def get_title_from_id(self, question_id):
            return "two-sum"

    class FakeHandler:
        def generate_submission_file(self):
            return "class Solution: ..."

    class FakeClient:
        calls = []

        def submit_question(self, *args):
            self.calls.append(args)

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ConfigManagerWithSource)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", RunQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.create_file_handler", lambda *_: FakeHandler())
    monkeypatch.setattr("leet2git.leet2git.LeetcodeClient", FakeClient)

    result = CliRunner().invoke(leet2git, ["run", "1"])

    assert result.exit_code == 0
    assert FakeClient.calls == [
        (
            "class Solution: ...",
            1,
            "two-sum",
            "python3",
            True,
            "[2,7,11,15]\n9\n[3,2,4]\n6",
        )
    ]


def test_run_reports_missing_question(monkeypatch):
    class RunQuestionDB(EmptyQuestionDB):
        def get_question(self, question_id):
            return None

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", FakeConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", RunQuestionDB)

    result = CliRunner().invoke(leet2git, ["run", "1"])

    assert result.exit_code == 0
    assert "Could not find the question with id 1" in result.output


def test_import_all_filters_pages_and_updates_readme(monkeypatch, tmp_path):
    class ConfigManagerWithSource(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

    class ImportQuestionDB(EmptyQuestionDB):
        instances = []

        def __init__(self, config):
            super().__init__(config)
            self.questions = {}
            self.save_count = 0
            self.instances.append(self)

        def add_question(self, question):
            self.questions[question.id] = question

        def check_if_exists(self, question_id):
            return question_id in self.questions

        def save(self):
            self.save_count += 1

        def get_sorted_list(self, sort_by):
            return sorted(self.questions.values(), key=lambda question: question.id)

    class FakeClient:
        def __init__(self):
            self.pages = [
                SubmissionListResponse.model_validate(
                    {
                        "submissions_dump": [
                            {
                                "title_slug": "two-sum",
                                "status_display": "Accepted",
                                "lang": "python3",
                                "timestamp": 10,
                                "code": "code one",
                            },
                            {
                                "title_slug": "three-sum",
                                "status_display": "Accepted",
                                "lang": "java",
                                "timestamp": 20,
                                "code": "code skipped",
                            },
                        ],
                        "has_next": True,
                        "last_key": "next-page",
                    }
                ),
                SubmissionListResponse.model_validate(
                    {
                        "submissions_dump": [
                            {
                                "title_slug": "add-two-numbers",
                                "status_display": "Accepted",
                                "lang": "python3",
                                "timestamp": 30,
                                "code": "code two",
                            },
                            {
                                "title_slug": "median-of-two-sorted-arrays",
                                "status_display": "Wrong Answer",
                                "lang": "python3",
                                "timestamp": 40,
                                "code": "code skipped",
                            },
                        ],
                        "has_next": False,
                        "last_key": "",
                    }
                ),
            ]

        def get_submission_list(self, last_key="", offset=0):
            assert (last_key, offset) in {("", 0), ("next-page", 20)}
            return self.pages[offset // 20]

    class FakeProcess:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            self.target(*self.args)

        def join(self):
            pass

    class FakeSyncManager:
        def start(self, initializer=None):
            if initializer:
                initializer()

        def dict(self):
            return {}

        def shutdown(self):
            pass

    class FakeReadmeHandler:
        built_lists = []

        def __init__(self, config):
            self.config = config

        def build_readme(self, question_list):
            self.built_lists.append(question_list)

    def fake_generate_files(ret_dict, qid, title_slug, lc, timestamp, config, code=""):
        ret_dict[qid] = QuestionData(
            id=qid,
            title=title_slug,
            title_slug=title_slug,
            creation_time=timestamp,
            raw_code=code,
        )

    title_ids = {
        "two-sum": 1,
        "three-sum": 15,
        "add-two-numbers": 2,
        "median-of-two-sorted-arrays": 4,
    }

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ConfigManagerWithSource)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", ImportQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.LeetcodeClient", FakeClient)
    monkeypatch.setattr("leet2git.leet2git.Process", FakeProcess)
    monkeypatch.setattr("leet2git.leet2git.SyncManager", FakeSyncManager)
    monkeypatch.setattr("leet2git.leet2git.ReadmeHandler", FakeReadmeHandler)
    monkeypatch.setattr("leet2git.leet2git.generate_files", fake_generate_files)
    monkeypatch.setattr(
        "leet2git.leet2git.get_question_id",
        lambda title_slug, qdb, lc: title_ids[title_slug],
    )
    monkeypatch.setattr("leet2git.leet2git.time.sleep", lambda _: None)

    result = CliRunner().invoke(leet2git, ["import-all"])

    imported_db = ImportQuestionDB.instances[-1]
    assert result.exit_code == 0
    assert "In total, 2 questions were imported!" in result.output
    assert sorted(imported_db.questions) == [1, 2]
    assert imported_db.questions[1].raw_code == "code one"
    assert imported_db.questions[2].raw_code == "code two"
    assert imported_db.save_count == 3
    assert [question.id for question in FakeReadmeHandler.built_lists[-1]] == [1, 2]


def test_init_can_create_repository(monkeypatch, tmp_path):
    class InitConfigManager(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path / "initial"))

        def reset_config(self, source_repository, language):
            self.config.source_path = source_repository
            self.config.language = language

    class FakeHandler:
        generated_repos = []

        def generate_repo(self, source_path):
            self.generated_repos.append(source_path)

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", InitConfigManager)
    monkeypatch.setattr("leet2git.leet2git.create_file_handler", lambda *_: FakeHandler())

    result = CliRunner().invoke(
        leet2git,
        ["init", "--source-repository", str(tmp_path / "repo"), "--language", "rust", "--create-repo"],
    )

    assert result.exit_code == 0
    assert FakeHandler.generated_repos == [str(tmp_path / "repo")]


def test_reset_soft_resets_database_after_confirmation(monkeypatch, tmp_path):
    class ResetConfigManager(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

        def reset_config(self, source_repository, language):
            self.config.source_path = source_repository
            self.config.language = language

    class ResetQuestionDB(EmptyQuestionDB):
        reset_count = 0

        def reset(self):
            self.__class__.reset_count += 1

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ResetConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", ResetQuestionDB)

    result = CliRunner().invoke(
        leet2git,
        ["reset", "--soft", "--source-repository", str(tmp_path), "--language", "python3"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert ResetQuestionDB.reset_count == 1


def test_reset_hard_removes_generated_files_and_regenerates_repo(monkeypatch, tmp_path):
    source_file = tmp_path / "src" / "leetcode_1_two_sum.py"
    test_file = tmp_path / "tests" / "test_1.py"
    source_file.parent.mkdir()
    test_file.parent.mkdir()
    source_file.write_text("solution\n", encoding="UTF8")
    test_file.write_text("test\n", encoding="UTF8")

    class ResetConfigManager(FakeConfigManager):
        def __init__(self):
            self.config = AppConfig(language="python3", source_path=str(tmp_path))

        def reset_config(self, source_repository, language):
            self.config.source_path = source_repository
            self.config.language = language

    class ResetQuestionDB(EmptyQuestionDB):
        reset_count = 0

        def reset(self):
            self.__class__.reset_count += 1

    class FakeHandler:
        generated_repos = []

        def generate_repo(self, source_path):
            self.generated_repos.append(source_path)

    monkeypatch.setattr("leet2git.leet2git.ConfigManager", ResetConfigManager)
    monkeypatch.setattr("leet2git.leet2git.QuestionDB", ResetQuestionDB)
    monkeypatch.setattr("leet2git.leet2git.create_file_handler", lambda *_: FakeHandler())

    result = CliRunner().invoke(
        leet2git,
        ["reset", "--hard", "--source-repository", str(tmp_path), "--language", "python3"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert not source_file.exists()
    assert not test_file.exists()
    assert ResetQuestionDB.reset_count == 1
    assert FakeHandler.generated_repos == [str(tmp_path)]
