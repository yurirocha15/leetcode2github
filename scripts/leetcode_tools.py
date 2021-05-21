import os
import platform
from pathlib import Path

import clize
from leetcode_client import LeetcodeClient
from python_handler import PythonHandler
from question_db import QuestionData, QuestionDB
from readme_handler import ReadmeHandler


def get_question(id: int):
    """Generates all the files for a question

    Args:
        id (int): the question id
    """
    # get question data
    lc = LeetcodeClient()
    try:
        data, is_new = lc.get_question_data(id)
    except ValueError as e:
        print(e.args)
        return

    if is_new:
        # generate
        py_handler = PythonHandler(data)
        py_handler.generate_source()
        py_handler.generete_tests()

        # store data
        qdb = QuestionDB()
        qdb.load()
        qdb.add_question(data)
        qdb.save()

        # update readme
        rh = ReadmeHandler()
        rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))


def submit_question(id: int):
    # submissions
    qdb = QuestionDB()
    qdb.load()
    problems = qdb.get_data()
    # create submit file
    if id in problems:
        lines = []
        with open(problems[id].file_path, "r", encoding="UTF8") as f:
            for line in f:
                if 'if __name__ == "__main__":' in line:
                    break
                lines.append(line)

        with open("tmp.py", "w", encoding="UTF8") as f:
            f.writelines(lines)

        lc = LeetcodeClient()
        try:
            lc.submit_question("tmp.py")
        except Exception as e:
            pass
        os.remove("tmp.py")

    else:
        print(f"Could not find the question with id {id}")


def leetcode_login():
    """Login to leetcode"""
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
    clize.run(get_question, submit_question, leetcode_login)
