import json
import os
import platform
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import browser_cookie3
import requests
from bs4 import BeautifulSoup
from question_db import IdTitleMap, QuestionData


class LeetcodeClient:
    """Handles getting data from leetcode"""

    def __init__(self):
        os_name = platform.system()
        if os_name == "Linux":
            self.binary_path = os.path.join("bin", "leetcode-cli", "linux", "leetcode-cli")
            self.divider = "/"
        elif os_name == "Windows":
            self.binary_path = os.path.join("bin", "leetcode-cli", "windows", "leetcode-cli.exe")
            self.divider = "\\"
        elif os_name == "Darwin":
            self.binary_path = os.path.join("bin", "leetcode-cli", "macos", "leetcode-cli")
            self.divider = "/"

    def login(self):
        """Login to leetcode using the leetcode-cli

        The file ~/.lc/leetcode/user.json needs to exist for this command to work
        """
        os.system(self.binary_path + " user -c")

    def logout(self):
        """Logout from leetcode"""
        os.system(self.binary_path + " user -L")

    def get_question_data(
        self,
        id: int,
        title_slug: str,
        language: str,
        code: Optional[str] = "",
        verbose: Optional[bool] = False,
    ) -> Tuple[QuestionData, bool]:
        """Gets the data from a question

        Args:
            id (int): the question id
            title_slug (str): the question title
            language str: the language to download the code
            code (Optional[str]): the question solution
            verbose (Optional[bool]): if true print information to the terminal

        Returns:
            QuestionData: The data needed to generate the question files
        """
        # get cookies
        cookies, _, _ = self.get_cookies()

        leetcode_question_data = self.scrap_question_data(title_slug, cookies)

        data = QuestionData(id=id, creation_time=time.time())

        data.title = leetcode_question_data["data"]["question"]["title"]
        data.url = (
            "https://leetcode.com/problems/" + leetcode_question_data["data"]["question"]["titleSlug"]
        )
        data.difficulty = leetcode_question_data["data"]["question"]["difficulty"]
        data.question_template = next(
            code["code"]
            for code in leetcode_question_data["data"]["question"]["codeSnippets"]
            if code["langSlug"] == language
        )
        data.categories = leetcode_question_data["data"]["question"]["topicTags"]
        soup = BeautifulSoup(
            leetcode_question_data["data"]["question"]["content"], features="html.parser"
        )
        data.description = soup.get_text().replace("\r\n", "\n").split("\n")
        num_of_inputs = len(leetcode_question_data["data"]["question"]["sampleTestCase"].split("\n"))
        inputs = leetcode_question_data["data"]["question"]["exampleTestcases"].split("\n")
        data.inputs = [
            ", ".join(inputs[i : i + num_of_inputs]) for i in range(0, len(inputs), num_of_inputs)
        ]
        tmp_description = []
        for line in data.description:
            if "Output: " in line:
                data.outputs.append(line[8:])
            if len(line) > 100:
                # split on commas or periods, while keeping them
                tmp_description.extend(re.split(r"(?<=[\.\,])\s*", line))
            else:
                tmp_description.append(line)

        data.description = tmp_description

        data.file_path = os.path.join(
            "src",
            f"leetcode_{data.id}_"
            + leetcode_question_data["data"]["question"]["titleSlug"].replace("-", "_"),
        )

        if code:
            data.raw_code = code

        return data, True

    def scrap_question_data(self, question_name: str, cookies: str) -> List[Dict[str, Any]]:
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

    def get_latest_submission(self, qid: str, cookies: str, language: str) -> str:
        url = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"

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

    def get_cookies(self) -> Tuple[str, str, str]:
        url = "https://leetcode.com/profile/"
        client = requests.session()
        try:
            browsers = (browser_cookie3.chrome(), browser_cookie3.firefox())
        except browser_cookie3.BrowserCookieError as e:
            print(e.args)

        for browser in browsers:
            try:
                r = client.get(url, cookies=browser)
                cookies = r.request.headers["Cookie"]
                csrftoken = client.cookies["csrftoken"]
                text = r.text
            except:
                continue
            if csrftoken:
                break

        return cookies, csrftoken, text

    def get_parsed_cookies(self) -> Tuple[str, str, str]:
        """Gets the cookies from the browser

        Raises:
            ValueError: if the user is not logger either on chrome or firefox

        Returns:
            Tuple[str, str, str]: the username and the cookies
        """
        cookies, csrftoken, text = self.get_cookies()
        leetcode_session = re.findall(r"LEETCODE_SESSION=(.*?);|$", cookies, flags=re.DOTALL)[0]
        username = re.findall(r"username: '(.*?)',", text, flags=re.DOTALL)[0]

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

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> Dict[str, Any]:
        cookies, _, _ = self.get_cookies()
        url = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

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

        response = requests.request("GET", url, headers=headers, data=payload)

        return json.loads(response.text)

    def get_id_title_map(self) -> IdTitleMap:
        """Get a dictionary that maps the id to the question title slug

        Returns:
            IdTitleMap: maps the id to the title slug
        """
        cookies, _, _ = self.get_cookies()
        url = "https://leetcode.com/api/problems/all/"

        payload = {}
        headers = {
            "authority": "leetcode.com",
            "pragma": "no-cache",
            "accept": "application/json",
            "cache-control": "no-cache",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "content-type": "application/json",
            "origin": "https://leetcode.com",
            "accept-language": "en-US,en;q=0.9",
            "cookie": cookies,
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        id_title_map: IdTitleMap = IdTitleMap()
        for stat in json.loads(response.text)["stat_status_pairs"]:
            if "frontend_question_id" in stat["stat"] and "question__title_slug" in stat["stat"]:
                id_title_map.id_to_title[int(stat["stat"]["frontend_question_id"])] = stat["stat"][
                    "question__title_slug"
                ]
                id_title_map.title_to_id[stat["stat"]["question__title_slug"]] = int(
                    stat["stat"]["frontend_question_id"]
                )

        return id_title_map


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848))
