"""
Handles the local question database
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import operator
import os
import pickle

import click
from pydantic import BaseModel, ConfigDict, Field

from leet2git.config_manager import AppConfig

DB_DIR_NAME = ".leet2git"
DB_FILE_NAME = "database.json"
LEGACY_QUESTION_DB_FILE = ".question_data.pkl"
LEGACY_ID_TITLE_MAP_FILE = ".id_title_map.pkl"
DB_VERSION = 1


class TopicTag(BaseModel):
    """LeetCode topic metadata attached to a question."""

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True)

    name: str = ""
    slug: str = ""
    translated_name: str | None = Field(default=None, alias="translatedName")
    typename: str | None = Field(default=None, alias="__typename")


class QuestionData(BaseModel):
    """Stores all the data related to a question"""

    model_config = ConfigDict(validate_assignment=True)

    title: str = ""
    title_slug: str = ""
    url: str = ""
    id: int = 0
    internal_id: int = 0
    creation_time: float = 0.0
    difficulty: str = ""
    file_path: str = ""
    test_file_path: str = ""
    question_template: str = ""
    raw_code: str = ""
    language: str = ""
    function_name: list[str] = Field(default_factory=list)
    description: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    categories: list[TopicTag] = Field(default_factory=list)

    def __setstate__(self, state: dict[str, object]) -> None:
        """Support unpickling state written by the former dataclass model."""
        if "__dict__" in state:
            super().__setstate__(state)
            return

        model = type(self).model_validate(state)
        object.__setattr__(self, "__dict__", model.__dict__)
        object.__setattr__(self, "__pydantic_fields_set__", set(state))
        object.__setattr__(self, "__pydantic_extra__", None)
        object.__setattr__(self, "__pydantic_private__", None)


class IdTitleMap(BaseModel):
    """Maps Ids and title slugs"""

    model_config = ConfigDict(validate_assignment=True)

    id_to_title: dict[int, str] = Field(default_factory=dict)
    title_to_id: dict[str, int] = Field(default_factory=dict)

    def __setstate__(self, state: dict[str, object]) -> None:
        """Support unpickling state written by the former dataclass model."""
        if "__dict__" in state:
            super().__setstate__(state)
            return

        model = type(self).model_validate(state)
        object.__setattr__(self, "__dict__", model.__dict__)
        object.__setattr__(self, "__pydantic_fields_set__", set(state))
        object.__setattr__(self, "__pydantic_extra__", None)
        object.__setattr__(self, "__pydantic_private__", None)


class DatabaseState(BaseModel):
    """Versioned persisted question database."""

    model_config = ConfigDict(validate_assignment=True)

    version: int = DB_VERSION
    questions: dict[int, QuestionData] = Field(default_factory=dict)
    id_title_map: IdTitleMap = Field(default_factory=IdTitleMap)


class QuestionDB:
    """Handles the question data"""

    def __init__(self, config: AppConfig):
        self.db_dir = os.path.join(config.source_path, DB_DIR_NAME)
        self.db_file = os.path.join(self.db_dir, DB_FILE_NAME)
        self.legacy_db_file = os.path.join(config.legacy_data_path, LEGACY_QUESTION_DB_FILE)
        self.legacy_id_title_map_file = os.path.join(
            config.legacy_data_path,
            LEGACY_ID_TITLE_MAP_FILE,
        )
        self.question_data_dict: dict[int, QuestionData] = {}
        self.id_title_map: IdTitleMap = IdTitleMap()
        self.migrated_from_legacy = False

    def load(self):
        """Load the question data from disk"""
        if os.path.isfile(self.db_file):
            with open(self.db_file, encoding="UTF8") as f:
                self._load_state(DatabaseState.model_validate_json(f.read()))
            return

        if os.path.isfile(self.legacy_db_file) or os.path.isfile(self.legacy_id_title_map_file):
            self._load_legacy_pickles()
            self.migrated_from_legacy = True
            self.save()
            click.secho(
                f"Migrated legacy question database into {self.db_file}.",
                fg="yellow",
            )

    def save(self):
        """Save the question data to disk"""
        os.makedirs(self.db_dir, exist_ok=True)
        state = DatabaseState(
            version=DB_VERSION,
            questions=self.question_data_dict,
            id_title_map=self.id_title_map,
        )
        with open(self.db_file, "w", encoding="UTF8") as f:
            f.write(state.model_dump_json(indent=2, by_alias=True))

    def get_data(self) -> dict[int, QuestionData]:
        """Returns the question data

        Returns:
            Dict[int, QuestionData]: A dictionary whose the question id is its key.
        """
        return self.question_data_dict

    def get_question(self, question_id: int) -> QuestionData | None:
        """get a question data if it exists

        Args:
            question_id (int): the question id

        Returns:
            Optional[QuestionData]: the question data
        """
        if self.check_if_exists(question_id):
            return self.question_data_dict[question_id]
        return None

    def add_question(self, qd: QuestionData):
        """Add a question to the dictionary

        Args:
            qd (QuestionData): The question data
        """
        self.question_data_dict[qd.id] = qd

    def delete_question(self, question_id: int):
        """Removes a question from the dictionary

        Args:
            question_id (int): the question id
        """
        if question_id in self.question_data_dict:
            self.question_data_dict.pop(question_id)

    def get_sorted_list(self, sort_by: str) -> list[QuestionData]:
        """Returns a sorted list with all the questions

        Args:
            sort_by (str): the attribute used to sort the list.
            Can be any QuestionData attribute.

        Returns:
            List[QuestionData]: [description]
        """
        return sorted(self.question_data_dict.values(), key=operator.attrgetter(sort_by))

    def check_if_exists(self, question_id: int) -> bool:
        """Checks if a question exists in the database

        Args:
            question_id (int): the question id

        Returns:
            bool: true if the question exists in the database
        """
        return question_id in self.question_data_dict

    def get_title_from_id(self, question_id: int) -> str:
        """Get the question title slug from its id

        Args:
            question_id (int): the question id

        Returns:
            str: the question title slug
        """
        if self.check_if_slug_is_known(question_id):
            return self.id_title_map.id_to_title[question_id]
        return ""

    def check_if_slug_is_known(self, question_id: int) -> bool:
        """Checks if the title slug is cached locally

        Args:
            question_id (int): the question id

        Returns:
            bool: true if the title slug is cached locally
        """
        return question_id in self.id_title_map.id_to_title

    def get_id_from_title(self, slug: str) -> int:
        """Get the question id from its title slug

        Args:
            str: the question title slug

        Returns:
            id (int): the question id
        """
        if self.check_if_id_is_known(slug):
            return self.id_title_map.title_to_id[slug]
        return -1

    def check_if_id_is_known(self, slug: str) -> bool:
        """Checks if the id is cached locally

        Args:
            str: the question title slug

        Returns:
            bool: true if the id sis cached locally
        """
        return slug in self.id_title_map.title_to_id

    def set_id_title_map(self, id_title_map: IdTitleMap):
        """Sets the id to slug dict

        Args:
            id_title_map (IdTitleMap):
                a dictionary mapping the question id to the title slug and vice-versa
        """
        self.id_title_map = id_title_map

    def reset(self):
        """Delete database"""
        self.question_data_dict: dict[int, QuestionData] = {}
        self.id_title_map: IdTitleMap = IdTitleMap()
        self.save()

    def _load_question_data(self, raw_data: object) -> dict[int, QuestionData]:
        """Normalize legacy pickle payloads into Pydantic models."""
        if not isinstance(raw_data, dict):
            return {}

        loaded_data: dict[int, QuestionData] = {}
        for question_id, question_data in raw_data.items():
            if not isinstance(question_id, int | str):
                continue
            loaded_data[int(question_id)] = (
                question_data
                if isinstance(question_data, QuestionData)
                else QuestionData.model_validate(question_data)
            )
        return loaded_data

    def _load_id_title_map(self, raw_data: object) -> IdTitleMap:
        """Normalize legacy pickle payloads into a Pydantic id/title map."""
        if isinstance(raw_data, IdTitleMap):
            return raw_data
        return IdTitleMap.model_validate(raw_data)

    def _load_state(self, state: DatabaseState) -> None:
        """Copy a versioned database state into this instance."""
        self.question_data_dict = state.questions
        self.id_title_map = state.id_title_map

    def _load_legacy_pickles(self) -> None:
        """Load legacy platform-path pickle files for one-way migration."""
        if os.path.isfile(self.legacy_db_file):
            with open(self.legacy_db_file, "rb") as f:
                self.question_data_dict = self._load_question_data(pickle.load(f))
        if os.path.isfile(self.legacy_id_title_map_file):
            with open(self.legacy_id_title_map_file, "rb") as f:
                self.id_title_map = self._load_id_title_map(pickle.load(f))
