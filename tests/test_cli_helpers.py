from leet2git.cli_helpers import get_question_id, reset_config, wait_to_finish_download
from leet2git.question_db import IdTitleMap, QuestionData


class FakeConfigManager:
    def __init__(self):
        self.reset_calls = []
        self.config = type("Config", (), {"source_path": "/old/repo"})()

    def reset_config(self, source_repository, language):
        self.reset_calls.append((source_repository, language))


def test_reset_config_reuses_existing_source_path():
    manager = FakeConfigManager()

    reset_config(manager, "", "python3")

    assert manager.reset_calls == [("/old/repo", "python3")]


def test_get_question_id_refreshes_unknown_slug_mapping():
    class FakeQuestionDB:
        def __init__(self):
            self.saved = False
            self.title_to_id = {}

        def check_if_id_is_known(self, title_slug):
            return title_slug in self.title_to_id

        def set_id_title_map(self, id_title_map):
            self.title_to_id = id_title_map.title_to_id

        def save(self):
            self.saved = True

        def get_id_from_title(self, title_slug):
            return self.title_to_id[title_slug]

    class FakeClient:
        def get_id_title_map(self):
            return IdTitleMap(title_to_id={"two-sum": 1})

    qdb = FakeQuestionDB()

    assert get_question_id("two-sum", qdb, FakeClient()) == 1
    assert qdb.saved is True


def test_wait_to_finish_download_joins_jobs_and_stores_results():
    class FakeProcess:
        joined = False

        def join(self):
            self.joined = True

    class FakeQuestionDB:
        def __init__(self):
            self.questions = []

        def add_question(self, question):
            self.questions.append(question)

    process = FakeProcess()
    question_db = FakeQuestionDB()

    imported_count = wait_to_finish_download([process], {1: QuestionData(id=1)}, question_db)

    assert imported_count == 1
    assert process.joined is True
    assert question_db.questions == [QuestionData(id=1)]
