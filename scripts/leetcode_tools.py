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
from pathlib import Path

import clize
from leetcode_client import LeetcodeClient
from my_utils import download_leetcode_cli, leetcode_cli_exists
from python_handler import PythonHandler
from question_db import QuestionData, QuestionDB


def get_question(id: int):
    if not leetcode_cli_exists():
        print("Please run 'make setup' to download the leetcode-cli")
        return

    # get question data
    lc = LeetcodeClient()
    data: QuestionData = lc.get_question_data(id)

    # generate
    py_handler = PythonHandler(data)
    py_handler.generate_source()
    py_handler.generete_tests()

    # store data
    qdb = QuestionDB()
    qdb.load()
    qdb.add_question(data)
    qdb.save()


def submit_question():
    pass


def download_client():
    if not leetcode_cli_exists():
        download_leetcode_cli()


def leetcode_login():
    home_folder = str(Path.home())
    lc = LeetcodeClient()
    # Logout. This erases the user.json file
    lc.logout()
    os_name = platform.system()
    if os_name in ["Linux", "Darwin"]:
        cmd = "mkdir -p "
    elif os_name == "Windows":
        cmd = "mkdir "
    os.system(cmd + os.path.join(home_folder, ".lc", "leetcode"))
    print("Make sure to login to leetcode on either chrome or firefox.")
    try:
        userid, leetcode_session, crsftoken = lc.get_leetcode_cookies()
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
        lc.login()
        print(f"Logged in as {userid}")


if __name__ == "__main__":
    clize.run(get_question, submit_question, download_client, leetcode_login)
