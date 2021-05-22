import os
import platform
from pathlib import Path
from typing import Dict

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
        data, is_new = lc.get_question_data(id, verbose=False)
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
        py_handler = PythonHandler(problems[id])
        file_to_submit = py_handler.generate_submission_file()

        lc = LeetcodeClient()
        try:
            lc.submit_question(file_to_submit)
        except Exception as e:
            print(e.args)

        os.remove(file_to_submit)

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
        userid, leetcode_session, crsftoken = lc.get_parsed_cookies()
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


def get_all_solutions():
    """Get all solutions and generate their files"""
    lc = LeetcodeClient()
    qdb = QuestionDB()
    qdb.load()
    has_next: bool = True
    last_key: str = ""
    offset: int = 0
    imported_cnt = 0
    slug_to_id_map: Dict[str, int] = {}
    try:
        while has_next:
            submissions = lc.get_submission_list(last_key, offset)
            for submission in submissions["submissions_dump"]:
                qid = -1
                if submission["title_slug"] in slug_to_id_map:
                    qid = slug_to_id_map[submission["title_slug"]]
                if submission[
                    "status_display"
                ] == "Accepted" and not qdb.check_if_exists(qid):
                    if qid == -1:
                        q_data = lc.scrap_question_data(
                            submission["title_slug"], lc.get_cookies()[0]
                        )
                        qid = q_data["data"]["question"]["questionFrontendId"]
                        slug_to_id_map[submission["title_slug"]] = qid
                    if not qdb.check_if_exists(qid):
                        try:
                            data, is_new = lc.get_question_data(
                                qid,
                                verbose=False,
                            )
                        except ValueError as e:
                            print(e.args)
                            return
                        if is_new:
                            # generate
                            data.creation_time = submission["timestamp"]
                            py_handler = PythonHandler(data)
                            py_handler.generate_source()
                            py_handler.generete_tests()

                            # store data
                            qdb.add_question(data)

                            imported_cnt += 1
                            print(
                                f"""The question "{qid}|{submission['title']}" was imported"""
                            )

            has_next = submissions["has_next"]
            last_key = submissions["last_key"]
            offset += 20
            qdb.save()
    except KeyboardInterrupt:
        print("Stopping the process...")
    except Exception as e:
        print(e.args)

    qdb.save()
    # update readme
    rh = ReadmeHandler()
    rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))

    print(f"In total, {imported_cnt} questions were imported!")


if __name__ == "__main__":
    clize.run(get_question, submit_question, leetcode_login, get_all_solutions)
