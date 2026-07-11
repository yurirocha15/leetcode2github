"""Randomly smoke-test public LeetCode problem imports without browser cookies.

The sampler is deliberately sequential and jittered to avoid request bursts. It
stops on rate limiting or access blocking instead of trying to work around it.
Generated files live in a temporary directory unless --keep-artifacts is used.
"""

import ast
import json
import math
import multiprocessing
import queue
import random
import runpy
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import click

from leet2git.config_manager import AppConfig
from leet2git.file_handler import create_file_handler
from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeClient
from leet2git.leetcode_models import ProblemListResponse
from leet2git.question_db import QuestionData
from leet2git.test_harness import get_local_test_limitation

MAX_RUNTIME_SECONDS = 3595.0
SHUTDOWN_RESERVE_SECONDS = 4.0
DIFFICULTY_NAMES = {1: "Easy", 2: "Medium", 3: "Hard"}
ERA_COUNT = 6


@dataclass(frozen=True)
class Candidate:
    """One public problem eligible for sampling."""

    question_id: int
    slug: str
    difficulty: str
    era: int


@dataclass
class ProblemResult:
    """Structured outcome for one attempted problem import."""

    question_id: int
    slug: str
    difficulty: str
    era: int
    status: str
    stage: str
    error_type: str = ""
    message: str = ""
    input_count: int = 0
    output_count: int = 0
    function_names: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    test_generated: bool = False
    elapsed_seconds: float = 0.0

    @classmethod
    def failure(
        cls,
        candidate: Candidate,
        stage: str,
        error: BaseException,
        elapsed_seconds: float = 0.0,
    ) -> "ProblemResult":
        """Build a concise failure result without response bodies or source code."""
        return cls(
            question_id=candidate.question_id,
            slug=candidate.slug,
            difficulty=candidate.difficulty,
            era=candidate.era,
            status="failed",
            stage=stage,
            error_type=type(error).__name__,
            message=_clean_message(str(error)),
            elapsed_seconds=elapsed_seconds,
        )


@dataclass(frozen=True)
class SamplerSettings:
    """Validated sampler limits and pacing."""

    percentage: float = 1.0
    max_seconds: float = MAX_RUNTIME_SECONDS
    min_delay: float = 2.0
    max_delay: float = 5.0
    request_timeout: float = 15.0
    item_timeout: float = 25.0
    language: str = "python3"

    def __post_init__(self) -> None:
        if not 0 < self.percentage <= 100:
            raise ValueError("percentage must be greater than 0 and at most 100")
        if not 1 <= self.max_seconds <= MAX_RUNTIME_SECONDS:
            raise ValueError(f"max_seconds must be between 1 and {MAX_RUNTIME_SECONDS:g}")
        if self.min_delay < 1:
            raise ValueError("min_delay must be at least 1 second")
        if self.max_delay < self.min_delay:
            raise ValueError("max_delay must be greater than or equal to min_delay")
        if self.request_timeout <= 0 or self.item_timeout <= 0:
            raise ValueError("timeouts must be positive")
        if self.language not in {"python", "python3"}:
            raise ValueError("the sampler currently supports python or python3")


@dataclass
class SamplerReport:
    """Aggregate sampler results suitable for JSON output."""

    seed: int
    percentage: float
    max_seconds: float
    catalog_total: int = 0
    eligible_free: int = 0
    paid_excluded: int = 0
    target_imports: int = 0
    attempted: int = 0
    imported: int = 0
    passed: int = 0
    soft_errors: int = 0
    skipped: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    stop_reason: str = ""
    difficulty_coverage: dict[str, int] = field(default_factory=dict)
    era_coverage: dict[str, int] = field(default_factory=dict)
    topic_coverage: list[str] = field(default_factory=list)
    results: list[ProblemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe report dictionary."""
        return asdict(self)

    def exit_code(self) -> int:
        """Return 0 for complete, 1 for hard failures, or 2 for incomplete runs."""
        if self.stop_reason.startswith("catalog:") or self.imported < self.target_imports:
            return 2
        if self.failed:
            return 1
        return 0


ProblemRunner = Callable[[Candidate, Path, str, float], ProblemResult]


class QuestionDataClient(Protocol):
    """Client behavior needed to inspect one public problem."""

    def get_question_data(
        self,
        question_id: int,
        title_slug: str,
        language: str,
        /,
    ) -> QuestionData: ...


class ProblemCatalogClient(Protocol):
    """Client behavior needed to build the public sampler population."""

    def get_problem_list(self) -> ProblemListResponse: ...


def build_population(catalog: ProblemListResponse) -> tuple[list[Candidate], int]:
    """Return free problems annotated with broad ID eras plus paid exclusion count."""
    free_rows = [row for row in catalog.stat_status_pairs if not row.paid_only]
    paid_count = len(catalog.stat_status_pairs) - len(free_rows)
    sorted_rows = sorted(free_rows, key=lambda row: row.stat.frontend_question_id)
    population: list[Candidate] = []
    seen_ids: set[int] = set()
    for index, row in enumerate(sorted_rows):
        question_id = row.stat.frontend_question_id
        slug = row.stat.question_title_slug
        if question_id <= 0 or not slug or question_id in seen_ids:
            continue
        seen_ids.add(question_id)
        era = min(ERA_COUNT - 1, index * ERA_COUNT // max(1, len(sorted_rows)))
        population.append(
            Candidate(
                question_id=question_id,
                slug=slug,
                difficulty=DIFFICULTY_NAMES.get(row.difficulty.level, "Unknown"),
                era=era,
            )
        )
    return population, paid_count


def varied_candidate_order(population: Sequence[Candidate], rng: random.Random) -> list[Candidate]:
    """Shuffle within difficulty/era strata, then round-robin across those strata."""
    buckets: dict[tuple[str, int], list[Candidate]] = defaultdict(list)
    for candidate in population:
        buckets[(candidate.difficulty, candidate.era)].append(candidate)
    for candidates in buckets.values():
        rng.shuffle(candidates)

    keys = list(buckets)
    rng.shuffle(keys)
    ordered: list[Candidate] = []
    while keys:
        next_keys: list[tuple[str, int]] = []
        for key in keys:
            candidates = buckets[key]
            if candidates:
                ordered.append(candidates.pop())
            if candidates:
                next_keys.append(key)
        rng.shuffle(next_keys)
        keys = next_keys
    return ordered


def inspect_problem(
    candidate: Candidate,
    output_root: Path,
    language: str,
    client: QuestionDataClient,
) -> ProblemResult:
    """Fetch one problem and exercise callable discovery, source, and test generation."""
    started = time.monotonic()
    stage = "fetch"
    try:
        data = client.get_question_data(candidate.question_id, candidate.slug, language)
        data.language = language
        if data.title_slug != candidate.slug or data.internal_id <= 0:
            raise ValueError("LeetCode returned mismatched question metadata")

        config = AppConfig(language=language, source_path=str(output_root))
        handler = create_file_handler(data, config)

        soft_error_stage = "test_generation"
        soft_error_type = "JudgeHarnessUnsupported"
        test_limitation = get_local_test_limitation(data)
        if not test_limitation:
            if not data.inputs or not data.outputs:
                test_limitation = "Could not parse both example inputs and outputs"
                soft_error_type = "MissingExamples"
            elif len(data.inputs) != len(data.outputs):
                test_limitation = f"Parsed {len(data.inputs)} inputs but {len(data.outputs)} outputs"
                soft_error_type = "ExampleCountMismatch"

        stage = "callable_discovery"
        try:
            data.function_name = handler.get_function_name()
        except Exception as error:
            if not test_limitation:
                test_limitation = f"Could not identify the callable: {_clean_message(str(error))}"
                soft_error_stage = stage
                soft_error_type = "CallableDiscoveryError"

        if test_limitation:
            data.requires_custom_test_harness = True

        stage = "source_generation"
        data.file_path = str(handler.generate_source())
        source_path = _safe_generated_path(output_root, data.file_path)
        source_symbols = _validate_python_file(source_path, execute=True)

        result = ProblemResult(
            question_id=candidate.question_id,
            slug=candidate.slug,
            difficulty=candidate.difficulty,
            era=candidate.era,
            status="passed",
            stage="complete",
            input_count=len(data.inputs),
            output_count=len(data.outputs),
            function_names=list(data.function_name),
            topics=sorted(tag.slug for tag in data.categories if tag.slug),
        )

        stage = "test_generation"
        if test_limitation:
            result.status = "soft_error"
            result.stage = soft_error_stage
            result.error_type = soft_error_type
            result.message = test_limitation
        else:
            try:
                data.test_file_path = handler.generate_tests()
                test_path = _safe_generated_path(output_root, data.test_file_path)
                _validate_python_file(test_path, execute=True)
                if len(data.function_name) > 1 and data.function_name[0] not in source_symbols:
                    raise ValueError(
                        f'Generated constructor "{data.function_name[0]}" is not module-level'
                    )
                result.test_generated = True
            except Exception as error:
                result.status = "soft_error"
                result.stage = stage
                result.error_type = type(error).__name__
                result.message = _clean_message(str(error))

        result.elapsed_seconds = round(time.monotonic() - started, 3)
        return result
    except LeetcodeAPIError as error:
        result = ProblemResult.failure(candidate, stage, error, round(time.monotonic() - started, 3))
        if f'"{language}" code snippet' in str(error):
            result.status = "skipped"
            result.stage = "snippet"
        return result
    except Exception as error:
        return ProblemResult.failure(candidate, stage, error, round(time.monotonic() - started, 3))


def run_problem_in_worker(
    candidate: Candidate,
    output_root: Path,
    language: str,
    timeout_seconds: float,
) -> ProblemResult:
    """Run one import in a killable subprocess so the global deadline remains bounded."""
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_problem_worker,
        args=(candidate, output_root, language, timeout_seconds, result_queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(1)
        result = ProblemResult.failure(
            candidate,
            "generation_timeout",
            TimeoutError(f"Problem import exceeded {timeout_seconds:.1f} seconds"),
            timeout_seconds,
        )
        result_queue.close()
        process.close()
        return result

    try:
        payload = result_queue.get(timeout=1)
    except queue.Empty:
        return ProblemResult.failure(
            candidate,
            "worker",
            RuntimeError(f"Worker exited with code {process.exitcode} without a result"),
        )
    finally:
        result_queue.close()
        process.close()
    return ProblemResult(**payload)


def run_sampler(
    settings: SamplerSettings,
    *,
    seed: int,
    catalog_client: ProblemCatalogClient | None = None,
    problem_runner: ProblemRunner = run_problem_in_worker,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    progress: Callable[[str], None] = click.echo,
    keep_artifacts: Path | None = None,
) -> SamplerReport:
    """Run a bounded, sequential sample and return its structured report."""
    started = clock()
    deadline = started + settings.max_seconds
    rng = random.Random(seed)
    report = SamplerReport(
        seed=seed,
        percentage=settings.percentage,
        max_seconds=settings.max_seconds,
    )
    client = catalog_client or LeetcodeClient(
        timeout=min(settings.request_timeout, max(1.0, settings.max_seconds - 1)),
        use_browser_cookies=False,
    )

    try:
        catalog = client.get_problem_list()
    except Exception as error:
        report.stop_reason = f"catalog: {_clean_message(str(error))}"
        report.duration_seconds = round(clock() - started, 3)
        return report

    population, paid_count = build_population(catalog)
    report.catalog_total = len(catalog.stat_status_pairs)
    report.eligible_free = len(population)
    report.paid_excluded = paid_count
    report.target_imports = min(
        len(population),
        max(1, math.ceil(len(population) * settings.percentage / 100)),
    )
    candidates = varied_candidate_order(population, rng)
    progress(
        f"seed={seed} free={report.eligible_free} paid_excluded={paid_count} "
        f"target={report.target_imports}"
    )

    temporary_directory: tempfile.TemporaryDirectory[str] | None = None
    if keep_artifacts is None:
        temporary_directory = tempfile.TemporaryDirectory(prefix="leet2git-sampler-")
        workspace = Path(temporary_directory.name)
    else:
        workspace = keep_artifacts.resolve()
        workspace.mkdir(parents=True, exist_ok=True)

    last_failure_fingerprint: tuple[str, str, str] | None = None
    repeated_failures = 0
    try:
        for candidate in candidates:
            if report.imported >= report.target_imports:
                break

            delay = rng.uniform(settings.min_delay, settings.max_delay)
            remaining = deadline - clock()
            if remaining <= delay + SHUTDOWN_RESERVE_SECONDS:
                report.stop_reason = "deadline reached before the next paced request"
                break
            sleeper(delay)
            remaining = deadline - clock()
            if remaining <= SHUTDOWN_RESERVE_SECONDS:
                report.stop_reason = "deadline reached"
                break

            item_timeout = min(
                settings.item_timeout,
                max(1.0, remaining - SHUTDOWN_RESERVE_SECONDS),
            )
            problem_root = workspace / f"{candidate.question_id}_{candidate.slug}"
            result = problem_runner(candidate, problem_root, settings.language, item_timeout)
            report.results.append(result)
            report.attempted += 1

            if result.status == "passed":
                report.passed += 1
                report.imported += 1
            elif result.status == "soft_error":
                report.soft_errors += 1
                report.imported += 1
            elif result.status == "skipped":
                report.skipped += 1
            else:
                report.failed += 1

            progress(
                f"[{report.imported}/{report.target_imports}] {result.status.upper():10} "
                f"#{candidate.question_id} {candidate.slug} ({result.stage})"
            )

            if _is_access_block(result):
                report.stop_reason = "LeetCode rate-limited or blocked the sampler; stopped"
                break

            if result.status == "failed":
                fingerprint = (result.stage, result.error_type, result.message)
                repeated_failures = (
                    repeated_failures + 1 if fingerprint == last_failure_fingerprint else 1
                )
                last_failure_fingerprint = fingerprint
                if repeated_failures >= 3:
                    report.stop_reason = "three identical failures in a row; circuit breaker opened"
                    break
            else:
                repeated_failures = 0
                last_failure_fingerprint = None
        else:
            report.stop_reason = "candidate catalog exhausted"
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()

    if report.imported < report.target_imports and not report.stop_reason:
        report.stop_reason = "target was not reached"
    _finalize_report(report, clock() - started)
    return report


def _problem_worker(
    candidate: Candidate,
    output_root: Path,
    language: str,
    timeout_seconds: float,
    result_queue: multiprocessing.Queue,
) -> None:
    """Child-process entry point for one public problem import."""
    client = LeetcodeClient(
        timeout=max(1.0, min(15.0, timeout_seconds - 1)),
        use_browser_cookies=False,
    )
    result = inspect_problem(candidate, output_root, language, client)
    result_queue.put(asdict(result))


def _safe_generated_path(root: Path, relative_path: str) -> Path:
    """Resolve a generated path and reject writes outside the temporary workspace."""
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if path != resolved_root and resolved_root not in path.parents:
        raise ValueError(f"Generated path escaped the sampler workspace: {relative_path}")
    if not path.is_file():
        raise FileNotFoundError(f"Generated file does not exist: {relative_path}")
    return path


def _validate_python_file(path: Path, *, execute: bool) -> set[str]:
    """Parse, compile, and optionally import a generated Python file."""
    source = path.read_text(encoding="UTF8")
    tree = ast.parse(source, filename=str(path))
    compile(tree, str(path), "exec")
    if not execute:
        return set()
    return set(runpy.run_path(str(path), run_name="leet2git_sampler_module"))


def _clean_message(message: str) -> str:
    """Keep reports concise and single-line."""
    return " ".join(message.split())[:500]


def _is_access_block(result: ProblemResult) -> bool:
    message = result.message.casefold()
    return result.status == "failed" and (
        "http 403" in message
        or "http 429" in message
        or "rate limit" in message
        or "too many requests" in message
        or "captcha" in message
    )


def _finalize_report(report: SamplerReport, duration_seconds: float) -> None:
    imported_results = [
        result for result in report.results if result.status in {"passed", "soft_error"}
    ]
    report.duration_seconds = round(duration_seconds, 3)
    report.difficulty_coverage = dict(
        sorted(Counter(result.difficulty for result in imported_results).items())
    )
    report.era_coverage = dict(
        sorted(Counter(str(result.era + 1) for result in imported_results).items())
    )
    report.topic_coverage = sorted({topic for result in imported_results for topic in result.topics})


@click.command()
@click.option(
    "--percentage",
    type=click.FloatRange(min=0.01, max=100),
    default=1.0,
    show_default=True,
    help="Percentage of the free public catalog to import.",
)
@click.option(
    "--max-minutes",
    type=click.FloatRange(min=0.5, max=60),
    default=60.0,
    show_default=True,
    help="Wall-clock limit; a shutdown reserve keeps the process under 60 minutes.",
)
@click.option(
    "--min-delay",
    type=click.FloatRange(min=1, max=30),
    default=2.0,
    show_default=True,
    help="Minimum delay between public problem requests.",
)
@click.option(
    "--max-delay",
    type=click.FloatRange(min=1, max=30),
    default=5.0,
    show_default=True,
    help="Maximum randomized delay between public problem requests.",
)
@click.option("--seed", type=int, help="Seed to reproduce the candidate order and jitter.")
@click.option(
    "--report",
    "report_path",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Optional path for the full JSON report.",
)
@click.option(
    "--keep-artifacts",
    type=click.Path(path_type=Path, file_okay=False),
    help="Keep generated sample files here instead of deleting the temporary workspace.",
)
def main(
    percentage: float,
    max_minutes: float,
    min_delay: float,
    max_delay: float,
    seed: int | None,
    report_path: Path | None,
    keep_artifacts: Path | None,
) -> None:
    """Sample public Python problem scaffolds and report import defects."""
    selected_seed = seed if seed is not None else random.SystemRandom().randrange(2**63)
    try:
        settings = SamplerSettings(
            percentage=percentage,
            max_seconds=min(max_minutes * 60, MAX_RUNTIME_SECONDS),
            min_delay=min_delay,
            max_delay=max_delay,
        )
    except ValueError as error:
        raise click.UsageError(str(error)) from error

    report = run_sampler(
        settings,
        seed=selected_seed,
        keep_artifacts=keep_artifacts,
    )
    report_json = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json + "\n", encoding="UTF8")
        click.echo(f"report={report_path}")
    click.echo(report_json)
    raise SystemExit(report.exit_code())


if __name__ == "__main__":
    main()
