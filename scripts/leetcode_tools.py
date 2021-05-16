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
import re
from pathlib import Path
from typing import List

import clize
from my_utils import (
    create_folder_if_needed,
    download_leetcode_cli,
    get_file_name,
    get_function_name,
    get_leetcode_cookies,
    leetcode_cli_exists,
)
from python_handler import PythonHandler
from question_db import QuestionData, QuestionDB


def get_question(id: int):
    if not leetcode_cli_exists():
        print("Please run 'make setup' to download the leetcode-cli")
        return

    data = QuestionData(id=id)
    os.system(
        os.path.join("bin", "dist", "leetcode-cli")
        + " show "
        + str(id)
        + " -gx -l python3 -o ./src > tmp.txt"
    )
    with open("tmp.txt", "r", encoding="UTF8") as f:
        for i, line in enumerate(f):
            print(line)
            if i == 0:
                data.title = " ".join(line.split()[1:])
            elif "Source Code:" in line:
                data.file_path = line.split()[3]
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

    os.remove("tmp.txt")
    new_file_path = (
        data.file_path.replace(".", "-", 1)
        .replace("/", "/leetcode-", 1)
        .replace("-", "_")
    )
    os.rename(data.file_path, new_file_path)
    data.file_path = new_file_path
    with open(data.file_path, "r") as f:
        text = f.read()
        data.function_name = re.findall(r"    def (.*?)\(self,", text)[0]
    # data.code[-1], data.function_name = get_function_name(data.code[-1])

    py_handler = PythonHandler(data)
    py_handler.generate_source()
    py_handler.generete_tests()

    # update readme
    with open("README.md", "r+") as f:
        for line in f:
            pass
        last_id = line.split()[0][1:]
        last_id = int(last_id) if last_id.isnumeric() else -1
        f.write(
            f"|{last_id + 1} |[{data.title}]({data.file_path})|{data.id}|{data.difficulty}|[Leetcode]({data.url})|\n"
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
