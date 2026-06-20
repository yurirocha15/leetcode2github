from leet2git.config_manager import AppConfig
from leet2git.default_handler import DefaultHandler
from leet2git.question_db import QuestionData


def test_default_handler_generates_source_in_parent_directories(tmp_path):
    question = QuestionData(
        id=2,
        title="Rust Problem",
        difficulty="Medium",
        url="https://leetcode.com/problems/rust-problem",
        file_path="src/leetcode_2_rust_problem",
        language="rust",
        question_template="impl Solution {}\n",
    )
    handler = DefaultHandler()
    handler.set_data(question, AppConfig(language="rust", source_path=str(tmp_path)))

    file_path = handler.generate_source()

    generated = tmp_path / file_path
    assert generated.exists()
    assert "impl Solution {}" in generated.read_text(encoding="UTF8")
