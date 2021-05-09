# to login copy firefox/chrome cookies
# add to ~/.lc/leetcode/user.json
# {
#   "login": <user>,
#   "loginCSRF": "",
#   "sessionCSRF": <csrftoken>,
#   "sessionId": <LEETCODE_SESSION>,
# }
# and run ./bin/dist/leetcode-cli user -c

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import clize
from autoimport import fix_files
from utils import (
    cammel_to_snake_case,
    create_folder_if_needed,
    download_leetcode_cli,
    get_file_name,
    get_leetcode_cookies,
    leetcode_cli_exists,
)


@dataclass
class QuestionData:
    title: str = ""
    url: str = ""
    id: int = 0
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    difficulty: str = ""
    function_name: str = ""
    file_name: str = ""
    code: List[str] = field(default_factory=list)


def get_question(id: int):
    if not leetcode_cli_exists():
        print("Please run 'make setup' to download the leetcode-cli")
        return

    data = QuestionData(id=id)
    os.system(
        os.path.join("bin", "dist", "leetcode-cli") + " show " + str(id) + " > tmp.txt"
    )
    with open("tmp.txt", "r", encoding="UTF8") as f:
        for i, line in enumerate(f):
            print(line)
            if i == 0:
                data.title = " ".join(line.split()[1:])
            elif "https://leetcode" in line:
                data.url = line[:-1]
            elif "Input: " in line:
                data.inputs.append(line[7:-1].replace("null", "None"))
            elif "Output: " in line:
                data.outputs.append(line[8:-1].replace("null", "None"))
            elif line[0] == "*":
                words = line.split()
                if words[1] in ["Easy", "Medium", "Hard"]:
                    data.difficulty = words[1]

    os.system(
        os.path.join("bin", "dist", "leetcode-cli")
        + " show -c -l python3 "
        + str(id)
        + " > tmp.txt"
    )
    with open("tmp.txt", "r") as f:
        for line in f:
            line = line.rstrip()
            if line:
                data.code.append(line)

    data.code[-1], data.function_name = cammel_to_snake_case(data.code[-1])

    print("Please, choose the folder to save the problem: ")
    folder = input()
    create_folder_if_needed(folder)
    os.remove("tmp.txt")

    # create file
    data.file_name = get_file_name(data.title)
    with open(os.path.join("src", f"{folder}_problems", data.file_name), "w") as f:
        f.write("#!/usr/bin/env python\n")
        f.write('"""\n')
        f.write("Platform: LeetCode\n")
        f.write(f"Problem: {data.id}. {data.title}\n")
        f.write(f"URL: {data.url}\n")
        f.write('"""\n')
        f.write("\n")
        f.write("\n")
        for line in data.code:
            f.write(line + "\n")
        f.write("        pass\n")
        f.write("\n")
        f.write("\n")
        f.write('if __name__ == "__main__":\n')
        f.write("    solution = Solution()\n")
        for i in range(len(data.inputs)):
            f.write(
                f"    assert"
                + (" not" if data.outputs[i] == "false" else "")
                + f" solution.{data.function_name}({data.inputs[i]})"
                + (
                    f" == {data.outputs[i]}"
                    if data.outputs[i] not in ["true", "false"]
                    else ""
                )
                + "\n"
            )
        f.write("")

    with open(os.path.join("src", f"{folder}_problems", data.file_name), "r+") as f:
        fix_files([f])

    # # create tests
    with open(os.path.join("src", f"{folder}_problems", f"test_{folder}.py"), "a") as f:
        f.write("\n")
        f.write("\n")
        f.write('"""\n')
        f.write(f"Test {data.id}. {data.title}\n")
        f.write('"""\n')
        f.write("\n")
        f.write("\n")
        f.write('@pytest.fixture(scope="session")\n')
        f.write(f"def init_variables_{data.id}():\n")
        f.write(
            f"    from src.{folder}_problems.{data.file_name[:-3]} import Solution\n"
        )
        f.write(f"    solution = Solution()\n")
        f.write("\n")
        f.write(f"    def _init_variables_{data.id}():\n")
        f.write("        return solution\n")
        f.write("\n")
        f.write(f"    yield _init_variables_{data.id}\n")
        f.write("\n")
        f.write(f"class TestClass{data.id}:")
        for i in range(len(data.inputs)):
            f.write("\n")
            f.write(f"    def test_solution_{i}(self, init_variables_{data.id}):\n")
            f.write(
                f"        assert"
                + (" not" if data.outputs[i] == "false" else "")
                + f" init_variables_{data.id}().{data.function_name}({data.inputs[i]})"
                + (
                    f" == {data.outputs[i]}"
                    if data.outputs[i] not in ["true", "false"]
                    else ""
                )
                + "\n"
            )

    with open(
        os.path.join("src", f"{folder}_problems", f"test_{folder}.py"), "r+"
    ) as f:
        fix_files([f])

    # update readme
    with open("README.md", "r+") as f:
        for line in f:
            pass
        last_id = line.split()[0][1:]
        last_id = int(last_id) if last_id.isnumeric() else -1
        f.write(
            f"|{last_id + 1} |[{data.title}](src/{folder}_problems/{data.file_name})|[{folder}](src/{folder}_problems)|{data.difficulty}|[Leetcode]({data.url})|\n"
        )


def submit_question():
    pass


def download_client():
    if not leetcode_cli_exists():
        download_leetcode_cli()


def leetcode_login():
    home_folder = str(Path.home())
    # Logout. This erases the user.json file
    os.system(os.path.join("bin", "dist", "leetcode-cli") + " user -L")
    os_name = platform.system()
    if os_name in ["Linux", "Darwin"]:
        cmd = "mkdir -p "
    elif os_name == "Windows":
        cmd = "mkdir "
    os.system(cmd + os.path.join(home_folder, ".lc", "leetcode"))
    print("Make sure to login to leetcode on either chrome or firefox.")
    try:
        userid, leetcode_session, crsftoken = get_leetcode_cookies()
    except ValueError as e:
        print(e.args)
    else:
        with open(os.path.join(home_folder, ".lc", "leetcode", "user.json"), "w") as f:
            f.write("{\n")
            f.write(f'    "login": "{userid}",\n')
            f.write('    "loginCSRF": "",\n')
            f.write(f'    "sessionCSRF": "{crsftoken}",\n')
            f.write(f'    "sessionId": "{leetcode_session}"\n')
            f.write("}")
        os.system(os.path.join("bin", "dist", "leetcode-cli") + " user -c")
        print(f"Logged in as {userid}")


if __name__ == "__main__":
    clize.run(get_question, submit_question, download_client, leetcode_login)
