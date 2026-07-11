import random

import pytest
from scripts.sample_leetcode_imports import (
    Candidate,
    ProblemResult,
    SamplerSettings,
    build_population,
    inspect_problem,
    run_sampler,
    varied_candidate_order,
)

from leet2git.leetcode_models import ProblemListResponse
from leet2git.question_db import QuestionData


def make_catalog(*rows: tuple[int, str, int, bool]) -> ProblemListResponse:
    return ProblemListResponse.model_validate(
        {
            "stat_status_pairs": [
                {
                    "stat": {
                        "frontend_question_id": question_id,
                        "question__title_slug": slug,
                    },
                    "difficulty": {"level": difficulty},
                    "paid_only": paid,
                }
                for question_id, slug, difficulty, paid in rows
            ]
        }
    )


def test_build_population_excludes_paid_and_assigns_id_eras():
    catalog = make_catalog(
        (1, "one", 1, False),
        (2, "two", 2, True),
        (100, "hundred", 3, False),
    )

    population, paid_count = build_population(catalog)

    assert paid_count == 1
    assert [(candidate.question_id, candidate.difficulty) for candidate in population] == [
        (1, "Easy"),
        (100, "Hard"),
    ]
    assert population[0].era == 0
    assert population[-1].era == 3


def test_varied_candidate_order_is_seeded_and_round_robins_strata():
    population = [
        Candidate(
            question_id=era * 10 + difficulty,
            slug=f"problem-{era}-{difficulty}",
            difficulty={1: "Easy", 2: "Medium", 3: "Hard"}[difficulty],
            era=era,
        )
        for era in range(6)
        for difficulty in range(1, 4)
    ]

    first = varied_candidate_order(population, random.Random(42))
    second = varied_candidate_order(population, random.Random(42))

    assert first == second
    assert len({(candidate.difficulty, candidate.era) for candidate in first[:18]}) == 18


@pytest.mark.parametrize(
    "settings",
    [
        {"percentage": 0},
        {"max_seconds": 3596},
        {"min_delay": 0.5},
        {"min_delay": 5, "max_delay": 4},
        {"language": "javascript"},
    ],
)
def test_sampler_settings_reject_unsafe_or_unsupported_values(settings):
    with pytest.raises(ValueError):
        SamplerSettings(**settings)


def test_inspect_problem_generates_and_validates_python_files(tmp_path, monkeypatch):
    class FakeClient:
        def get_question_data(self, question_id, slug, language):
            return QuestionData(
                id=question_id,
                internal_id=1,
                title="Two Sum",
                title_slug=slug,
                difficulty="Easy",
                file_path="src/leetcode_1_two_sum",
                language=language,
                question_template=("class Solution:\n    def twoSum(self, nums, target):\n"),
                inputs=["[2,7,11,15], 9"],
                outputs=["[0,1]"],
            )

    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr("leet2git.python_handler.PythonHandler.run_formatter", lambda *_: None)
    candidate = Candidate(1, "two-sum", "Easy", 0)

    result = inspect_problem(candidate, tmp_path, "python3", FakeClient())

    assert result.status == "passed"
    assert result.stage == "complete"
    assert result.function_names == ["twoSum"]
    assert result.test_generated is True
    assert (tmp_path / "src" / "leetcode_1_two_sum.py").is_file()
    assert (tmp_path / "tests" / "test_1.py").is_file()


def test_inspect_problem_reports_non_module_constructor_as_soft_error(tmp_path, monkeypatch):
    class FakeClient:
        def get_question_data(self, question_id, slug, language):
            return QuestionData(
                id=question_id,
                internal_id=297,
                title="Serialize and Deserialize Binary Tree",
                title_slug=slug,
                difficulty="Hard",
                file_path="src/leetcode_297_serialize_and_deserialize_binary_tree",
                language=language,
                question_template=(
                    "class Codec:\n"
                    "    def serialize(self, root):\n"
                    "        pass\n"
                    "    def deserialize(self, data):\n"
                    "        pass\n"
                ),
                inputs=['["Codec","serialize","deserialize"], [[],[None],[""]]'],
                outputs=['[null,"",null]'],
            )

    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr("leet2git.python_handler.PythonHandler.run_formatter", lambda *_: None)
    candidate = Candidate(297, "serialize-and-deserialize-binary-tree", "Hard", 1)

    result = inspect_problem(candidate, tmp_path, "python3", FakeClient())

    assert result.status == "soft_error"
    assert result.stage == "test_generation"
    assert "not module-level" in result.message


def test_inspect_problem_classifies_judge_supplied_types_as_unsupported_tests(tmp_path, monkeypatch):
    class FakeClient:
        def get_question_data(self, question_id, slug, language):
            return QuestionData(
                id=question_id,
                internal_id=987,
                title="Vertical Traversal",
                title_slug=slug,
                difficulty="Hard",
                file_path="src/leetcode_987_vertical_traversal",
                language=language,
                question_template=(
                    "# class TreeNode:\n"
                    "#     pass\n"
                    "class Solution:\n"
                    "    def verticalTraversal(self, root: TreeNode | None):\n"
                ),
                inputs=["root = [3,9,20,None,None,15,7]"],
                outputs=["[[9],[3,15],[20],[7]]"],
            )

    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr("leet2git.python_handler.PythonHandler.run_formatter", lambda *_: None)
    candidate = Candidate(987, "vertical-order-traversal-of-a-binary-tree", "Hard", 1)

    result = inspect_problem(candidate, tmp_path, "python3", FakeClient())

    assert result.status == "soft_error"
    assert result.stage == "test_generation"
    assert result.error_type == "JudgeHarnessUnsupported"
    assert "TreeNode" in result.message
    assert (tmp_path / "src" / "leetcode_987_vertical_traversal.py").is_file()
    assert not (tmp_path / "tests" / "test_987.py").exists()


def test_inspect_problem_classifies_custom_output_metadata_as_unsupported(tmp_path, monkeypatch):
    class FakeClient:
        def get_question_data(self, question_id, slug, language):
            return QuestionData(
                id=question_id,
                internal_id=27,
                title="Remove Element",
                title_slug=slug,
                difficulty="Easy",
                file_path="src/leetcode_27_remove_element",
                language=language,
                question_template=(
                    "class Solution:\n    def removeElement(self, nums, val):\n        pass\n"
                ),
                inputs=["[3,2,2,3], 3"],
                outputs=["2, nums = [2,2,_,_]"],
                requires_custom_test_harness=True,
            )

    monkeypatch.setattr("leet2git.python_handler.fix_files", lambda _: None)
    monkeypatch.setattr("leet2git.python_handler.PythonHandler.run_formatter", lambda *_: None)
    candidate = Candidate(27, "remove-element", "Easy", 0)

    result = inspect_problem(candidate, tmp_path, "python3", FakeClient())

    assert result.status == "soft_error"
    assert result.stage == "test_generation"
    assert result.error_type == "JudgeHarnessUnsupported"
    assert "custom or in-place output validation" in result.message
    assert (tmp_path / "src" / "leetcode_27_remove_element.py").is_file()
    assert not (tmp_path / "tests" / "test_27.py").exists()


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeCatalogClient:
    def __init__(self, catalog: ProblemListResponse):
        self.catalog = catalog

    def get_problem_list(self) -> ProblemListResponse:
        return self.catalog


def passing_result(candidate: Candidate, *_args) -> ProblemResult:
    return ProblemResult(
        question_id=candidate.question_id,
        slug=candidate.slug,
        difficulty=candidate.difficulty,
        era=candidate.era,
        status="passed",
        stage="complete",
        topics=["array"],
    )


def soft_error_result(candidate: Candidate, *_args) -> ProblemResult:
    return ProblemResult(
        question_id=candidate.question_id,
        slug=candidate.slug,
        difficulty=candidate.difficulty,
        era=candidate.era,
        status="soft_error",
        stage="test_generation",
        error_type="JudgeHarnessUnsupported",
        message="LeetCode supplies judge-only class definitions: TreeNode",
        topics=["binary-tree"],
    )


def test_run_sampler_reaches_percentage_target_with_seeded_pacing(tmp_path):
    catalog = make_catalog(
        (1, "one", 1, False),
        (2, "two", 2, False),
        (3, "three", 3, False),
        (4, "four", 1, False),
    )
    clock = FakeClock()
    progress: list[str] = []

    report = run_sampler(
        SamplerSettings(
            percentage=50,
            max_seconds=30,
            min_delay=1,
            max_delay=1,
            item_timeout=5,
        ),
        seed=7,
        catalog_client=FakeCatalogClient(catalog),
        problem_runner=passing_result,
        clock=clock,
        sleeper=clock.sleep,
        progress=progress.append,
        keep_artifacts=tmp_path,
    )

    assert report.target_imports == 2
    assert report.attempted == 2
    assert report.imported == 2
    assert report.duration_seconds == 2
    assert report.exit_code() == 0
    assert report.topic_coverage == ["array"]
    assert progress[0].startswith("seed=7")


def test_run_sampler_counts_soft_errors_as_imported_and_exits_successfully(tmp_path):
    catalog = make_catalog((1, "one", 1, False))
    clock = FakeClock()

    report = run_sampler(
        SamplerSettings(
            percentage=100,
            max_seconds=10,
            min_delay=1,
            max_delay=1,
            item_timeout=5,
        ),
        seed=3,
        catalog_client=FakeCatalogClient(catalog),
        problem_runner=soft_error_result,
        clock=clock,
        sleeper=clock.sleep,
        progress=lambda _: None,
        keep_artifacts=tmp_path,
    )

    assert report.imported == 1
    assert report.soft_errors == 1
    assert report.passed == 0
    assert report.failed == 0
    assert report.exit_code() == 0
    assert report.topic_coverage == ["binary-tree"]


def test_sampler_catalog_failure_is_incomplete_not_success(tmp_path):
    class FailingCatalogClient:
        def get_problem_list(self):
            raise RuntimeError("catalog unavailable")

    report = run_sampler(
        SamplerSettings(max_seconds=10, min_delay=1, max_delay=1),
        seed=4,
        catalog_client=FailingCatalogClient(),
        progress=lambda _: None,
        keep_artifacts=tmp_path,
    )

    assert report.stop_reason == "catalog: catalog unavailable"
    assert report.exit_code() == 2


def test_completed_sampler_reports_hard_failures_even_after_reaching_target(tmp_path):
    catalog = make_catalog((1, "one", 1, False), (2, "two", 2, False))
    clock = FakeClock()
    calls = 0

    def fail_then_pass(candidate: Candidate, *_args) -> ProblemResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return ProblemResult.failure(candidate, "source_generation", OSError("disk error"))
        return passing_result(candidate)

    report = run_sampler(
        SamplerSettings(
            percentage=50,
            max_seconds=20,
            min_delay=1,
            max_delay=1,
            item_timeout=5,
        ),
        seed=5,
        catalog_client=FakeCatalogClient(catalog),
        problem_runner=fail_then_pass,
        clock=clock,
        sleeper=clock.sleep,
        progress=lambda _: None,
        keep_artifacts=tmp_path,
    )

    assert report.imported == report.target_imports == 1
    assert report.failed == 1
    assert report.passed == 1
    assert report.exit_code() == 1


def test_run_sampler_stops_before_deadline_without_shortening_delay(tmp_path):
    catalog = make_catalog(
        (1, "one", 1, False),
        (2, "two", 2, False),
        (3, "three", 3, False),
        (4, "four", 1, False),
    )
    clock = FakeClock()

    report = run_sampler(
        SamplerSettings(
            percentage=50,
            max_seconds=7,
            min_delay=2,
            max_delay=2,
            item_timeout=1,
        ),
        seed=9,
        catalog_client=FakeCatalogClient(catalog),
        problem_runner=passing_result,
        clock=clock,
        sleeper=clock.sleep,
        progress=lambda _: None,
        keep_artifacts=tmp_path,
    )

    assert report.attempted == 1
    assert report.imported == 1
    assert report.duration_seconds <= 7
    assert "deadline" in report.stop_reason
    assert report.exit_code() == 2


def test_run_sampler_stops_immediately_on_rate_limit(tmp_path):
    catalog = make_catalog((1, "one", 1, False), (2, "two", 2, False))
    clock = FakeClock()

    def rate_limited(candidate: Candidate, *_args) -> ProblemResult:
        return ProblemResult(
            question_id=candidate.question_id,
            slug=candidate.slug,
            difficulty=candidate.difficulty,
            era=candidate.era,
            status="failed",
            stage="fetch",
            error_type="LeetcodeAPIError",
            message="LeetCode request failed with HTTP 429",
        )

    report = run_sampler(
        SamplerSettings(
            percentage=100,
            max_seconds=30,
            min_delay=1,
            max_delay=1,
            item_timeout=5,
        ),
        seed=2,
        catalog_client=FakeCatalogClient(catalog),
        problem_runner=rate_limited,
        clock=clock,
        sleeper=clock.sleep,
        progress=lambda _: None,
        keep_artifacts=tmp_path,
    )

    assert report.attempted == 1
    assert report.failed == 1
    assert "rate-limited" in report.stop_reason
    assert report.exit_code() == 2
