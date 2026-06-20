"""
Handles the local question database
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import operator
import os
import pickle
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    categories: list[dict[str, Any]] = Field(default_factory=list)

    def __setstate__(self, state: dict[str, Any]) -> None:
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

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Support unpickling state written by the former dataclass model."""
        if "__dict__" in state:
            super().__setstate__(state)
            return

        model = type(self).model_validate(state)
        object.__setattr__(self, "__dict__", model.__dict__)
        object.__setattr__(self, "__pydantic_fields_set__", set(state))
        object.__setattr__(self, "__pydantic_extra__", None)
        object.__setattr__(self, "__pydantic_private__", None)


class QuestionDB:
    """Handles the question data"""

    def __init__(self, config: dict[str, Any]):
        self.db_file = os.path.join(config["data_path"], ".question_data.pkl")
        self.id_title_map_file = os.path.join(config["data_path"], ".id_title_map.pkl")
        self.question_data_dict: dict[int, QuestionData] = {}
        self.id_title_map: IdTitleMap = IdTitleMap()

    def load(self):
        """Load the question data from disk"""
        if os.path.isfile(self.db_file):
            with open(self.db_file, "rb") as f:
                self.question_data_dict = self._load_question_data(pickle.load(f))
        if os.path.isfile(self.id_title_map_file):
            with open(self.id_title_map_file, "rb") as f:
                self.id_title_map = self._load_id_title_map(pickle.load(f))

    def save(self):
        """Save the question data to disk"""
        with open(self.db_file, "wb") as f:
            pickle.dump(self.question_data_dict, f)
        with open(self.id_title_map_file, "wb") as f:
            pickle.dump(self.id_title_map, f)

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

    def _load_question_data(self, raw_data: Any) -> dict[int, QuestionData]:
        """Normalize legacy pickle payloads into Pydantic models."""
        if not isinstance(raw_data, dict):
            return {}

        return {
            int(question_id): (
                question_data
                if isinstance(question_data, QuestionData)
                else QuestionData.model_validate(question_data)
            )
            for question_id, question_data in raw_data.items()
        }

    def _load_id_title_map(self, raw_data: Any) -> IdTitleMap:
        """Normalize legacy pickle payloads into a Pydantic id/title map."""
        if isinstance(raw_data, IdTitleMap):
            return raw_data
        return IdTitleMap.model_validate(raw_data)
