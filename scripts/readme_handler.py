from dataclasses import dataclass, field
from functools import reduce
from typing import Dict, List

from question_db import QuestionData, QuestionDB


@dataclass
class ReadmeTable:
    title: str = ""
    fields: List[str] = field(default_factory=list)
    values: List[List[str]] = field(default_factory=list)


class ReadmeHandler:
    def __init__(self):
        self.readme_file = "QUESTIONS.md"

    def build_readme(self):
        question_list = self.get_question_data()
        readme_table_dict: Dict[str, ReadmeTable] = {}
        main_table = ReadmeTable(
            title="Solution Summary",
            fields=["ID", "Problem", "Leetcode ID", "Categories", "Difficulty"],
        )
        for question in question_list:
            categories_str = ""
            for c in question.categories:
                categories_str += f"[{c['name']}](#{c['slug']}), "
                if c["slug"] not in readme_table_dict:
                    readme_table_dict[c["slug"]] = ReadmeTable(
                        title=f"""<a name="{c['slug']}"></a>{c['name']}""",
                        fields=["ID", "Problem", "Leetcode ID", "Difficulty"],
                    )
                readme_table_dict[c["slug"]].values.append(
                    [
                        str(len(readme_table_dict[c["slug"]].values) + 1),
                        f"[{question.title}]({question.file_path})",
                        f"[{question.id}]({question.url})",
                        question.difficulty,
                    ]
                )
            categories_str = categories_str[:-2]

            main_table.values.append(
                [
                    str(len(main_table.values) + 1),
                    f"[{question.title}]({question.file_path})",
                    f"[{question.id}]({question.url})",
                    categories_str,
                    question.difficulty,
                ]
            )

            self.dump_tables(main_table, readme_table_dict)

    def get_question_data(self) -> List[QuestionData]:
        qdb = QuestionDB()
        qdb.load()
        return qdb.get_sorted_list(sort_by="creation_time")

    def dump_tables(self, main_table: ReadmeTable, tables: Dict[str, ReadmeTable]):
        with open(self.readme_file, "w") as f:
            f.write(f"# {main_table.title}\n")
            f.write("\n")
            f.write("|" + "|".join(main_table.fields) + "|\n")
            f.write(
                "|:--:|"
                + "|".join(["--" for _ in range(len(main_table.fields) - 1)])
                + "|\n"
            )

            for value in main_table.values:
                f.write("|" + "|".join(value) + "|\n")

            f.write("\n")
            f.write("# Categories\n")
            for table in sorted(tables.items()):
                f.write(f"## {table[1].title}\n")
                f.write("\n")
                f.write("|" + "|".join(table[1].fields) + "|\n")
                f.write(
                    "|:--:|"
                    + "|".join(["--" for _ in range(len(table[1].fields) - 1)])
                    + "|\n"
                )
                for value in table[1].values:
                    f.write("|" + "|".join(value) + "|\n")


if __name__ == "__main__":
    rh = ReadmeHandler()
    rh.build_readme()
