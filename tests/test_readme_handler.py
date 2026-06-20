from leet2git.config_manager import AppConfig, ReadmeConfig
from leet2git.question_db import QuestionData, TopicTag
from leet2git.readme_handler import ReadmeHandler


def test_readme_handler_builds_summary_difficulty_and_category_tables(tmp_path):
    config = AppConfig(source_path=str(tmp_path))
    questions = [
        QuestionData(
            id=1,
            title="Two Sum",
            difficulty="Easy",
            url="https://leetcode.com/problems/two-sum",
            file_path="src/leetcode_1_two_sum.py",
            categories=[TopicTag(name="Array", slug="array")],
        ),
        QuestionData(
            id=2,
            title="Add Two Numbers",
            difficulty="Medium",
            url="https://leetcode.com/problems/add-two-numbers",
            file_path="src/leetcode_2_add_two_numbers.py",
            categories=[TopicTag(name="Linked List", slug="linked-list")],
        ),
    ]

    ReadmeHandler(config).build_readme(questions)

    readme = (tmp_path / "README.md").read_text(encoding="UTF8")
    assert "# <a name='summary'></a>Solution Summary" in readme
    assert "[Two Sum](src/leetcode_1_two_sum.py)" in readme
    assert "[Easy](#Easy)" in readme
    assert "# <a name='difficulty'></a>Difficulty" in readme
    assert '## <a name="array"></a>Array' in readme
    assert "[Array](#array)" in readme


def test_readme_handler_can_disable_anchor_sections(tmp_path):
    config = AppConfig(
        source_path=str(tmp_path),
        readme=ReadmeConfig(show_difficulty=False, show_category=False),
    )
    question = QuestionData(
        id=1,
        title="Two Sum",
        difficulty="Easy",
        url="https://leetcode.com/problems/two-sum",
        file_path="src/leetcode_1_two_sum.py",
        categories=[TopicTag(name="Array", slug="array")],
    )

    ReadmeHandler(config).build_readme([question])

    readme = (tmp_path / "README.md").read_text(encoding="UTF8")
    assert "[Difficulty](#difficulty)" not in readme
    assert "[Categories](#categories)" not in readme
    assert (
        "|1|[Two Sum](src/leetcode_1_two_sum.py)|[1](https://leetcode.com/problems/two-sum)|Array|Easy|"
        in readme
    )
