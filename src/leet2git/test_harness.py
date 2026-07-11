"""Classify LeetCode examples that need judge-specific local test support."""

import re

from leet2git.question_db import QuestionData

_COMMENTED_CLASS = re.compile(r"^\s*#\s*class\s+([A-Za-z_]\w*)\b", re.MULTILINE)
_UNSUPPORTED_HARNESS_TOPICS = frozenset({"concurrency", "interactive"})


def get_local_test_limitation(data: QuestionData) -> str:
    """Return why generic local tests are unsafe, or an empty string when supported."""
    judge_classes = sorted(set(_COMMENTED_CLASS.findall(data.question_template)))
    if judge_classes:
        return "LeetCode supplies judge-only class definitions: " + ", ".join(judge_classes)

    topics = {tag.slug for tag in data.categories if tag.slug}
    special_topics = sorted(_UNSUPPORTED_HARNESS_TOPICS.intersection(topics))
    if special_topics:
        return "LeetCode requires a judge-specific harness for: " + ", ".join(special_topics)

    if data.requires_custom_test_harness:
        return "LeetCode uses custom or in-place output validation"

    return ""
