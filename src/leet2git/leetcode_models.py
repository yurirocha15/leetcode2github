"""Typed LeetCode API request and response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from leet2git.question_db import TopicTag


class QuestionDataVariables(BaseModel):
    """Variables for the questionData GraphQL query."""

    title_slug: str = Field(alias="titleSlug")


class QuestionDataRequest(BaseModel):
    """GraphQL questionData request body."""

    model_config = ConfigDict(populate_by_name=True)

    operation_name: Literal["questionData"] = Field(default="questionData", alias="operationName")
    variables: QuestionDataVariables
    query: str


class CodeSnippet(BaseModel):
    """Starter code returned by LeetCode for one language."""

    model_config = ConfigDict(populate_by_name=True)

    lang: str = ""
    lang_slug: str = Field(alias="langSlug")
    code: str
    typename: str | None = Field(default=None, alias="__typename")


class QuestionPayload(BaseModel):
    """Question payload returned by the questionData query."""

    model_config = ConfigDict(populate_by_name=True)

    question_id: str = Field(alias="questionId")
    title: str
    title_slug: str = Field(alias="titleSlug")
    content: str
    difficulty: str
    example_testcases: str = Field(alias="exampleTestcases")
    sample_test_case: str = Field(alias="sampleTestCase")
    topic_tags: list[TopicTag] = Field(alias="topicTags")
    code_snippets: list[CodeSnippet] = Field(alias="codeSnippets")


class QuestionDataBody(BaseModel):
    """Nested data field for questionData."""

    question: QuestionPayload | None


class QuestionDataResponse(BaseModel):
    """Root questionData GraphQL response."""

    data: QuestionDataBody


class SubmissionRow(BaseModel):
    """Submission row returned by the submissions list endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    title_slug: str
    status_display: str
    lang: str
    timestamp: float
    code: str


class SubmissionListResponse(BaseModel):
    """Submissions list response."""

    submissions_dump: list[SubmissionRow]
    has_next: bool
    last_key: str


class ProblemStat(BaseModel):
    """Problem stat entry returned by the problem-list endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    frontend_question_id: int
    question_title_slug: str = Field(alias="question__title_slug")


class ProblemStatusPair(BaseModel):
    """Problem list row."""

    stat: ProblemStat


class ProblemListResponse(BaseModel):
    """Problem-list endpoint response."""

    stat_status_pairs: list[ProblemStatusPair]


class SubmitSolutionPayload(BaseModel):
    """Payload for submit and interpret endpoints."""

    model_config = ConfigDict(populate_by_name=True)

    question_id: int
    lang: str
    typed_code: str
    data_input: str | None = None
    judge_type: str | None = None


class SubmitSolutionResponse(BaseModel):
    """Submit endpoint response."""

    submission_id: int


class InterpretSolutionResponse(BaseModel):
    """Interpret endpoint response."""

    interpret_id: str


class SubmissionResultResponse(BaseModel):
    """Polling response for a submitted or interpreted solution."""

    state: str
    status_msg: str | None = None
    status_code: int | None = None
    status_runtime: str | None = None
    status_memory: str | None = None
    runtime_percentile: float | None = None
    memory_percentile: float | None = None
    input_formatted: str | None = None
    expected_output: str | None = None
    code_output: str | list[str] | None = None
    last_testcase: str | None = None
    runtime_error: str | None = None
    compile_error: str | None = None
