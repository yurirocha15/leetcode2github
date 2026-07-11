import pytest

from leet2git.leetcode_models import TopicTag
from leet2git.question_db import QuestionData
from leet2git.test_harness import get_local_test_limitation


@pytest.mark.parametrize("judge_type", ["TreeNode", "ListNode", "NestedInteger"])
def test_local_test_limitation_detects_judge_provided_classes(judge_type):
    data = QuestionData(question_template=f"# class {judge_type}:\n#     pass\n")

    assert judge_type in get_local_test_limitation(data)


@pytest.mark.parametrize("topic", ["interactive", "concurrency"])
def test_local_test_limitation_detects_judge_harness_topics(topic):
    data = QuestionData(categories=[TopicTag(name=topic.title(), slug=topic)])

    assert topic in get_local_test_limitation(data)


def test_local_test_limitation_detects_custom_output_and_accepts_ordinary_problem():
    custom = QuestionData(requires_custom_test_harness=True)
    ordinary = QuestionData(question_template="class Solution:\n    pass\n")

    assert "custom or in-place" in get_local_test_limitation(custom)
    assert get_local_test_limitation(ordinary) == ""
