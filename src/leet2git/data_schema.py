"""
Data Schema to validate requests
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
from enum import Enum, IntEnum
from typing import List, Optional

from pydantic.dataclasses import dataclass


class Difficulty(str, Enum):
    """Difficulty enum"""

    easy = "Easy"
    medium = "Medium"
    hard = "Hard"


class SubmissionStatusCodes(IntEnum):
    """Submission status code enum"""

    SUCCESS = 10
    WRONG_ANSWER = 11
    MEMORY_LIMIT_EXCEEDED = 12
    OUTPUT_LIMIT_EXCEEDED = 13
    TIME_LIMIT_EXCEEDED = 14
    RUNTIME_ERROR = 15
    COMPILE_ERROR = 20
    UNKNOWN_ERROR = 21


@dataclass
class CodeSnippet:
    """Code snippet data"""

    lang: str
    langSlug: str
    code: str


@dataclass
class TopicTags:
    """Topic tags data"""

    name: str
    slug: str


@dataclass
class LeetcodeQuestionData:
    """Leetcode question data"""

    questionId: str
    questionFrontendId: str
    title: str
    titleSlug: str
    content: str
    isPaidOnly: bool
    difficulty: Difficulty
    codeSnippets: List[CodeSnippet]
    topicTags: List[TopicTags]
    sampleTestCase: str
    exampleTestcases: str


@dataclass
class LeetcodeSubmissionResult:
    """Leetcode submission result"""

    state: str
    status_msg: str
    status_code: SubmissionStatusCodes
    submission_id: str
    lang: str
    pretty_lang: str
    run_success: bool
    question_id: str
    elapsed_time: int
    task_finish_time: int
    status_runtime: str
    memory: int
    status_memory: str
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    total_testcases: Optional[int] = None
    total_correct: Optional[int] = None
    compare_result: Optional[str] = None
    code_output: Optional[str] = None
    std_output: Optional[str] = None
    last_testcase: Optional[str] = None
    expected_output: Optional[str] = None
    # runtime error
    runtime_error: Optional[str] = None
    full_runtime_error: Optional[str] = None
    # compile error
    compile_error: Optional[str] = None
    full_compile_error: Optional[str] = None
    # wrong answer
    input_formatted: Optional[str] = None
    input: Optional[str] = None
