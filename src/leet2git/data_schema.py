"""
Data Schema to validate requests
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
from enum import Enum, IntEnum
from typing import List, Optional

from pydantic import BaseModel


class Difficulty(Enum):
    """Difficulty enum"""

    easy = "Easy"
    medium = "Medium"
    hard = "Hard"


# add a parser for the different difficulty return formats
def _Difficulty_Parser(cls, value) -> Difficulty:
    if isinstance(value, dict):
        if "level" in value:
            return Difficulty(value["level"])
        return Difficulty.easy
    if isinstance(value, int):
        return {1: Difficulty.easy, 2: Difficulty.medium, 3: Difficulty.hard}.get(
            value, Difficulty.easy
        )
    return super(Difficulty, cls).__new__(cls, value)


setattr(Difficulty, "__new__", _Difficulty_Parser)


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


class CodeSnippet(BaseModel):
    """Code snippet data"""

    lang: str
    langSlug: str
    code: str


class TopicTags(BaseModel):
    """Topic tags data"""

    name: str
    slug: str


class LeetcodeQuestionData(BaseModel):
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


class LeetcodeSubmissionResult(BaseModel):
    """Leetcode submission result"""

    state: str
    status_msg: str
    status_code: SubmissionStatusCodes
    submission_id: str
    lang: str
    pretty_lang: str
    run_success: bool
    elapsed_time: int
    task_finish_time: int
    status_runtime: str
    memory: int
    status_memory: str
    question_id: Optional[str] = None
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


class LeetcodeProblemStatus(BaseModel):
    """Leetcode problem status"""

    question_id: int
    frontend_question_id: int
    is_new_question: bool
    question__title: str
    question__title_slug: str


class LeetcodeProblemStatusPair(BaseModel):
    """Leetcode problem status pair"""

    stat: LeetcodeProblemStatus
    difficulty: Difficulty
    paid_only: bool
    is_favor: bool


class LeetcodeAllProblems(BaseModel):
    """Leetcode get all problems response"""

    user_name: str
    num_total: int
    num_solved: int
    stat_status_pairs: List[LeetcodeProblemStatusPair]
