import operator
import pickle
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class QuestionData:
    title: str = ""
    url: str = ""
    id: int = 0
    creation_time: float = 0.0
    difficulty: str = ""
    function_name: str = ""
    file_path: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)


class QuestionDB:
    """Handles the question data"""

    def __init__(self):
        self.db_file = "bin/question_data.pkl"
        self.question_data_dict: Dict[int, QuestionData] = {}

    def load(self):
        """Load the question data from disk"""
        self.question_data_dict = pickle.load(open(self.db_file, "wb"))

    def save(self):
        """Save the question data to disk"""
        pickle.dump(self.db_file, open(self.db_file, "rb"))

    def get_data(self) -> Dict[int, QuestionData]:
        """Returns the question data

        Returns:
            Dict[int, QuestionData]: A dictionary whose the question id is its key.
        """
        return self.question_data_dict

    def add_question(self, qd: QuestionData):
        """Add a question to the dictionary

        Args:
            qd (QuestionData): The question data
        """
        self.question_data_dict[qd.id] = qd

    def get_sorted_list(self, sort_by: str) -> List[QuestionData]:
        """Returns a sorted list with all the questions

        Args:
            sort_by (str): the attribute used to sort the list.
            Can be any QuestionData attribute.

        Returns:
            List[QuestionData]: [description]
        """
        return sorted(
            self.question_data_dict.values(), key=operator.attrgetter(sort_by)
        )
