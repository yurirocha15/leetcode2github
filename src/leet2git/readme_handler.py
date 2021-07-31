"""
Handles the REAMDE generation
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from leet2git.question_db import QuestionData, QuestionDB


@dataclass
class ReadmeTable:
    """Data related to a table"""

    title: str = ""
    fields: List[str] = field(default_factory=list)
    values: List[List[str]] = field(default_factory=list)


class ReadmeHandler:
    """Updates the README with the solved questions"""

    def __init__(self, config: Dict[str, Any]):
        self.readme_file: str = os.path.join(config["source_path"], "README.md")
        self.print_categories: bool = config["readme"]["show_category"]
        self.print_difficulty: bool = config["readme"]["show_difficulty"]

    def build_readme(self, question_list: List[QuestionData]):
        """Updates the README file

        Args:
            question_list (List[QuestionData]): a sorted list with the question data
        """

        category_tables: Dict[str, ReadmeTable] = {}
        difficulty_tables: Dict[str, ReadmeTable] = {
            "Easy": ReadmeTable(
                title='<a name="Easy"></a>Easy Questions',
                fields=["ID", "Problem", "Leetcode ID", "Categories"],
            ),
            "Medium": ReadmeTable(
                title='<a name="Medium"></a>Medium Questions',
                fields=["ID", "Problem", "Leetcode ID", "Categories"],
            ),
            "Hard": ReadmeTable(
                title='<a name="Hard"></a>Hard Questions',
                fields=["ID", "Problem", "Leetcode ID", "Categories"],
            ),
        }
        main_table = ReadmeTable(
            title="Solution Summary",
            fields=["ID", "Problem", "Leetcode ID", "Categories", "Difficulty"],
        )
        for question in question_list:
            difficulty_str = ""
            if self.print_difficulty:
                difficulty_str = f"[{question.difficulty}](#{question.difficulty})"
            else:
                difficulty_str = question.difficulty
            categories_str = ""
            for c in question.categories:
                if self.print_categories:
                    categories_str += f"[{c['name']}](#{c['slug']}), "
                    if c["slug"] not in category_tables:
                        category_tables[c["slug"]] = ReadmeTable(
                            title=f"""<a name="{c['slug']}"></a>{c['name']}""",
                            fields=["ID", "Problem", "Leetcode ID", "Difficulty"],
                        )
                    category_tables[c["slug"]].values.append(
                        [
                            str(len(category_tables[c["slug"]].values) + 1),
                            f"[{question.title}]({question.file_path})",
                            f"[{question.id}]({question.url})",
                            difficulty_str,
                        ]
                    )
                else:
                    categories_str += c["name"] + ", "

            categories_str = categories_str[:-2]
            if not question.difficulty:
                question.difficulty = "Easy"
            difficulty_tables[question.difficulty].values.append(
                [
                    str(len(difficulty_tables[question.difficulty].values) + 1),
                    f"[{question.title}]({question.file_path})",
                    f"[{question.id}]({question.url})",
                    categories_str,
                ]
            )
            main_table.values.append(
                [
                    str(len(main_table.values) + 1),
                    f"[{question.title}]({question.file_path})",
                    f"[{question.id}]({question.url})",
                    categories_str,
                    difficulty_str,
                ]
            )

        self.dump_tables(main_table, category_tables, difficulty_tables)

    def dump_tables(
        self,
        main_table: ReadmeTable,
        category_tables: Dict[str, ReadmeTable],
        difficulty_tables: Dict[str, ReadmeTable],
    ):
        """Generates the README file

        Args:
            main_table (ReadmeTable): the table containing all questions
            category_tables (Dict[str, ReadmeTable]): a dictionary with tables separated by category
            difficulty_tables (Dict[str, ReadmeTable]): a dictionary with tables separated by difficulty
        """
        with open(self.readme_file, "w", encoding="UTF8") as f:

            f.write("# Table of Contents\n")
            f.write(f"[{main_table.title}](#summary)\n")
            if self.print_difficulty:
                f.write("[Difficulty](#difficulty)\n")
            if self.print_categories:
                f.write("[Categories](#categories)\n")

            f.write(f"# <a name='summary'></a>{main_table.title}\n")
            f.write("\n")
            f.write("|" + "|".join(main_table.fields) + "|\n")
            f.write("|:--:|" + "|".join(["--" for _ in range(len(main_table.fields) - 1)]) + "|\n")

            for value in main_table.values:
                f.write("|" + "|".join(value) + "|\n")

            f.write("\n")
            if self.print_difficulty:
                f.write("# <a name='difficulty'></a>Difficulty\n")
                for difficulty in ("Easy", "Medium", "Hard"):
                    f.write(f"## {difficulty_tables[difficulty].title}\n")
                    f.write("\n")
                    f.write("|" + "|".join(difficulty_tables[difficulty].fields) + "|\n")
                    f.write(
                        "|:--:|"
                        + "|".join(["--" for _ in range(len(difficulty_tables[difficulty].fields) - 1)])
                        + "|\n"
                    )
                    for value in difficulty_tables[difficulty].values:
                        f.write("|" + "|".join(value) + "|\n")

                f.write("\n")
            if self.print_categories:
                f.write("# <a name='categories'></a>Categories\n")
                for table in sorted(category_tables.items()):
                    f.write(f"## {table[1].title}\n")
                    f.write("\n")
                    f.write("|" + "|".join(table[1].fields) + "|\n")
                    f.write(
                        "|:--:|" + "|".join(["--" for _ in range(len(table[1].fields) - 1)]) + "|\n"
                    )
                    for value in table[1].values:
                        f.write("|" + "|".join(value) + "|\n")

            f.write("\n")
            f.write("\n")
            f.write(
                "Automatically generated using \
                    [Leet2Git](https://github.com/yurirocha15/leetcode2github).\n"
            )


if __name__ == "__main__":
    from leet2git.config_manager import ConfigManager

    cm = ConfigManager()
    config = cm.config
    qdb = QuestionDB(config)
    qdb.load()
    rh = ReadmeHandler(config)
    rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))
