"""
Handles the local question database
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import operator
import os
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuestionData:
    """Stores all the data related to a question"""

    title: str = ""
    url: str = ""
    id: int = 0
    internal_id: int = 0
    creation_time: float = 0.0
    difficulty: str = ""
    file_path: str = ""
    test_file_path = ""
    question_template: str = ""
    raw_code: str = ""
    language: str = ""
    function_name: List[str] = field(default_factory=list)
    description: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    categories: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class IdTitleMap:
    """Maps Ids and title slugs"""

    id_to_title: Dict[int, str] = field(default_factory=dict)
    title_to_id: Dict[str, int] = field(default_factory=dict)


class QuestionDB:
    """Handles the question data"""

    def __init__(self, config: Dict[str, Any]):
        self.db_file = os.path.join(config["data_path"], ".question_data.pkl")
        self.id_title_map_file = os.path.join(config["data_path"], ".id_title_map.pkl")
        self.question_data_dict: Dict[int, QuestionData] = {}
        self.id_title_map: IdTitleMap = IdTitleMap()

    def load(self):
        """Load the question data from disk"""
        if os.path.isfile(self.db_file):
            with open(self.db_file, "rb") as f:
                self.question_data_dict = pickle.load(f)
        if os.path.isfile(self.id_title_map_file):
            with open(self.id_title_map_file, "rb") as f:
                self.id_title_map = pickle.load(f)

    def save(self):
        """Save the question data to disk"""
        with open(self.db_file, "wb") as f:
            pickle.dump(self.question_data_dict, f)
        with open(self.id_title_map_file, "wb") as f:
            pickle.dump(self.id_title_map, f)

    def get_data(self) -> Dict[int, QuestionData]:
        """Returns the question data

        Returns:
            Dict[int, QuestionData]: A dictionary whose the question id is its key.
        """
        return self.question_data_dict

    def get_question(self, question_id: int) -> Optional[QuestionData]:
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

    def get_sorted_list(self, sort_by: str) -> List[QuestionData]:
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
        self.question_data_dict: Dict[int, QuestionData] = {}
        self.id_title_map: IdTitleMap = IdTitleMap()
        self.save()
