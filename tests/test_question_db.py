import pickle

from leet2git.question_db import IdTitleMap, QuestionData, QuestionDB


def test_question_data_uses_isolated_defaults():
    first = QuestionData(id=1)
    second = QuestionData(id=2)

    first.inputs.append("[1, 2]")
    first.categories.append({"name": "Array", "slug": "array"})

    assert second.inputs == []
    assert second.categories == []


def test_question_data_validates_and_coerces_fields():
    question = QuestionData.model_validate(
        {
            "id": "42",
            "internal_id": "9001",
            "creation_time": "12.5",
            "function_name": ["twoSum"],
        }
    )

    assert question.id == 42
    assert question.internal_id == 9001
    assert question.creation_time == 12.5
    assert question.function_name == ["twoSum"]


def test_question_db_round_trips_pydantic_models(tmp_path):
    config = {"data_path": str(tmp_path)}
    question_db = QuestionDB(config)
    question_db.add_question(QuestionData(id=1, title="Two Sum"))
    question_db.set_id_title_map(IdTitleMap(id_to_title={1: "two-sum"}, title_to_id={"two-sum": 1}))
    question_db.save()

    loaded_db = QuestionDB(config)
    loaded_db.load()

    assert loaded_db.get_question(1) == QuestionData(id=1, title="Two Sum")
    assert loaded_db.get_title_from_id(1) == "two-sum"
    assert loaded_db.get_id_from_title("two-sum") == 1


def test_question_db_loads_legacy_dict_payloads(tmp_path):
    config = {"data_path": str(tmp_path)}
    question_db = QuestionDB(config)

    with open(question_db.db_file, "wb") as file:
        pickle.dump({1: {"id": "1", "title": "Two Sum"}}, file)
    with open(question_db.id_title_map_file, "wb") as file:
        pickle.dump({"id_to_title": {"1": "two-sum"}, "title_to_id": {"two-sum": "1"}}, file)

    question_db.load()

    assert question_db.get_question(1) == QuestionData(id=1, title="Two Sum")
    assert question_db.get_title_from_id(1) == "two-sum"
    assert question_db.get_id_from_title("two-sum") == 1


def test_question_data_unpickles_dataclass_style_state():
    question = QuestionData.__new__(QuestionData)
    question.__setstate__({"id": "7", "title": "Reverse Integer"})

    assert question == QuestionData(id=7, title="Reverse Integer")
