import json
import os
import platform
import re
import time
from typing import Any, Dict, List, Tuple

import browser_cookie3
import requests
from question_db import QuestionData, QuestionDB


class LeetcodeClient:
    """Handles getting data from leetcode"""

    def __init__(self):
        os_name = platform.system()
        if os_name == "Linux":
            self.binary_path = os.path.join(
                "bin", "leetcode-cli", "linux", "leetcode-cli"
            )
            self.divider = "/"
        elif os_name == "Windows":
            self.binary_path = os.path.join(
                "bin", "leetcode-cli", "windows", "leetcode-cli.exe"
            )
            self.divider = "\\"
        elif os_name == "Darwin":
            self.binary_path = os.path.join(
                "bin", "leetcode-cli", "macos", "leetcode-cli"
            )
            self.divider = "/"

    def login(self):
        """Login to leetcode using the leetcode-cli

        The file ~/.lc/leetcode/user.json needs to exist for this command to work
        """
        os.system(self.binary_path + " user -c")

    def logout(self):
        """Logout from leetcode"""
        os.system(self.binary_path + " user -L")

    def get_question_data(self, id: int) -> Tuple[QuestionData, bool]:
        """Gets the data from a question

        Args:
            id (int): the question id

        Returns:
            QuestionData: The data needed to generate the question files
        """
        qdb = QuestionDB()
        qdb.load()
        question_data = qdb.get_data()
        if id in question_data:
            print("Question already imported")
            return question_data[id], False

        data = QuestionData(id=id, creation_time=time.time())
        os.system(
            self.binary_path + " show " + str(id) + " -gx -l python3 -o ./src > tmp.txt"
        )
        with open("tmp.txt", "r", encoding="UTF8") as f:
            for i, line in enumerate(f):
                print(line)
                if "[ERROR]" in line:
                    raise ValueError(line)

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
        split_path = data.file_path.split(self.divider)
        split_path[-1] = (
            ("leetcode_" + split_path[-1]).replace(".", "_", 1).replace("-", "_")
        )
        new_file_path = os.path.join(*split_path)
        os.rename(data.file_path, new_file_path)
        data.file_path = new_file_path

        # get cookies
        url = "https://leetcode.com/profile/"
        client = requests.session()
        r = client.get(url, cookies=browser_cookie3.chrome())
        cookies = r.request.headers["Cookie"]

        leetcode_question_data = self.scrap_question_data(
            data.url.split("/")[-3], cookies
        )
        data.categories = leetcode_question_data["data"]["question"]["topicTags"]
        data.raw_code = self.get_latest_submission(
            leetcode_question_data["data"]["question"]["questionId"], cookies
        )
        tmp_function_name = re.findall(r"    def (.*?)\(self,", data.raw_code)
        if tmp_function_name:
            data.function_name = tmp_function_name[0]
        else:
            with open(data.file_path, "r", encoding="UTF8") as f:
                text = f.read()
                data.function_name = re.findall(r"    def (.*?)\(self,", text)[0]
        return data, True

    def scrap_question_data(
        self, question_name: str, cookies: str
    ) -> List[Dict[str, Any]]:
        """Query a question information

        Args:
            question_name (str): the question slug (which is inside the leetcode url)

        Returns:
            List[Dict[str, str]]: the categories information
        """
        url = "https://leetcode.com/graphql"

        payload = json.dumps(
            {
                "operationName": "questionData",
                "variables": {"titleSlug": question_name},
                "query": "query questionData($titleSlug: String) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    questionFrontendId\n    boundTopicId\n    title\n    titleSlug\n    content\n    translatedTitle\n    translatedContent\n    isPaidOnly\n    difficulty\n    likes\n    dislikes\n    isLiked\n    similarQuestions\n    exampleTestcases\n    contributors {\n      username\n      profileUrl\n      avatarUrl\n      __typename\n    }\n    topicTags {\n      name\n      slug\n      translatedName\n      __typename\n    }\n    companyTagStats\n    codeSnippets {\n      lang\n      langSlug\n      code\n      __typename\n    }\n    stats\n    hints\n    solution {\n      id\n      canSeeDetail\n      paidOnly\n      hasVideoSolution\n      paidOnlyVideo\n      __typename\n    }\n    status\n    sampleTestCase\n    metaData\n    judgerAvailable\n    judgeType\n    mysqlSchemas\n    enableRunCode\n    enableTestMode\n    enableDebugger\n    envInfo\n    libraryUrl\n    adminUrl\n    __typename\n  }\n}\n",
            }
        )
        headers = {
            "authority": "leetcode.com",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://leetcode.com",
            "cookie": cookies,
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return json.loads(response.text)

    def get_latest_submission(self, qid: str, cookies: str) -> str:
        url = f"https://leetcode.com/submissions/latest/?qid=" + qid + "&lang=python3"

        payload = {}
        headers = {
            "authority": "leetcode.com",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "accept": "application/json",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "origin": "https://leetcode.com",
            "accept-language": "en-US,en;q=0.9",
            "cookie": cookies,
        }
        raw_code = ""
        try:
            response = requests.request("GET", url, headers=headers, data=payload)
            raw_code = json.loads(response.text)["code"]
        except Exception as e:
            print(e.args)
        return raw_code

    def get_leetcode_cookies(self) -> Tuple[str, str, str]:
        """Gets the cookies from the browser

        Raises:
            ValueError: if the user is not logger either on chrome or firefox

        Returns:
            Tuple[str, str, str]: the username and the cookies
        """
        url = "https://leetcode.com/profile/"
        leetcode_session: str = ""
        csrftoken: str = ""
        username: str = ""
        try:
            browsers = (browser_cookie3.chrome(), browser_cookie3.firefox())
        except browser_cookie3.BrowserCookieError as e:
            print(e.args)

        for browser in browsers:
            try:
                client = requests.session()
                r = client.get(url, cookies=browser)
                cookies = r.request.headers["Cookie"]
                csrftoken = client.cookies["csrftoken"]
            except:
                continue
            leetcode_session = re.findall(
                r"LEETCODE_SESSION=(.*?);|$", cookies, flags=re.DOTALL
            )[0]
            username = re.findall(r"username: '(.*?)',", r.text, flags=re.DOTALL)[0]
            if leetcode_session and csrftoken and username:
                break

        if not leetcode_session or not csrftoken or not username:
            raise ValueError(
                "ERROR: Could not find the cookies neither on Chrome nor Firefox."
                + " Make sure to login to leetcode in one of these browsers."
            )

        return username, leetcode_session, csrftoken

    def submit_question(self, file: str):
        """Submit question to Leetcode

        Args:
            file (str): the path to the file which will be submited
        """
        os.system(self.binary_path + " submit " + file)


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848))
