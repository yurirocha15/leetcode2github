"""
Data Schema to validate requests
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
from enum import Enum
from typing import List

from pydantic.dataclasses import dataclass


class Difficulty(str, Enum):
    """Difficulty enum"""

    easy = "Easy"
    medium = "Medium"
    hard = "Hard"


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
