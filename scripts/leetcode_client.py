import json
import os
import platform
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import browser_cookie3
import requests
from bs4 import BeautifulSoup
from question_db import IdTitleMap, QuestionData


class LeetcodeClient:
    """Handles getting data from leetcode"""

    def __init__(self):
        os_name = platform.system()
        if os_name in ["Linux", "Darwin"]:
            self.divider = "/"
        elif os_name == "Windows":
            self.divider = "\\"

        self.cookies, self.csrftoken = self.get_cookies()

    def get_cookies(self) -> Tuple[str, str]:
        """Get the cookies from the browser

        Returns:
            Tuple[str, str]: the raw cookies and the csrftoken
        """
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
            except:
                continue
            if csrftoken:
                break

        return cookies, csrftoken

    def get_headers(self) -> Dict[str, str]:
        """Return the headers needed to call leetcode api

        Returns:
            Dict[str, str]: the call headers
        """
        headers = {
            "authority": "leetcode.com",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "content-type": "application/json",
            "accept": "*/*",
            "referer": "https://leetcode.com",
            "origin": "https://leetcode.com",
            "x-csrftoken": self.csrftoken,
            "cookie": self.cookies,
        }

        return headers

    def get_question_data(
        self, id: int, title_slug: str, language: str, code: Optional[str] = ""
    ) -> Tuple[QuestionData, bool]:
        """Gets the data from a question

        Args:
            id (int): the question id
            title_slug (str): the question title
            language str: the language to download the code
            code (Optional[str]): the question solution

        Returns:
            QuestionData: The data needed to generate the question files
        """

        leetcode_question_data = self.scrap_question_data(title_slug)

        data = QuestionData(id=id, creation_time=time.time())
        data.internal_id = int(leetcode_question_data["data"]["question"]["questionId"])
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
        example_started = False
        for idx, line in enumerate(data.description):
            if re.match(r"\s*Example\s*[0-9]*:", line):
                example_started = True
            elif "Output: " in line and example_started:
                data.outputs.append(line[8:])
                example_started = False
            elif line == "Output" and example_started:
                data.outputs.append(data.description[idx + 1].strip())
                example_started = False

            if len(line) > 100:
                # split on commas or periods, while keeping them
                split_line = re.split(r"(?<=[\.\,])\s*", line)
                tmp_line = ""
                for phrase in split_line:
                    if len(tmp_line) + len(phrase) <= 100:
                        tmp_line += phrase
                    else:
                        tmp_description.append(tmp_line)
                        tmp_line = ""
                if tmp_line:
                    tmp_description.append(tmp_line)
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

    def scrap_question_data(self, question_name: str) -> List[Dict[str, Any]]:
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

        response = requests.request("POST", url, headers=self.get_headers(), data=payload)
        return json.loads(response.text)

    def get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question

        Args:
            qid (str): the question id
            cookies (str): leetcode cookies
            language (str): the code language

        Returns:
            str: the submitted code
        """
        url = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"

        payload = {}
        raw_code = ""
        try:
            response = requests.request("GET", url, headers=self.get_headers(), data=payload)
            raw_code = json.loads(response.text)["code"]
        except Exception as e:
            print(e.args)
        return raw_code

    def submit_question(self, code: str, internal_id: str, language: str):
        """Submit question to Leetcode

        Args:
            code (str): the code which will be submitted
            internal_id (str): the question "questionId". (different from "frontend_id")
            language (str): the language of the code
        """

        url = "https://leetcode.com/problems/two-sum/submit/"

        payload = json.dumps(
            {
                "question_id": internal_id,
                "lang": language,
                "typed_code": code,
            }
        )

        response = requests.request("POST", url, headers=self.get_headers(), data=payload)
        submission_id: int = json.loads(response.text)["submission_id"]
        print("Waiting for submission results...")
        url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"

        payload = {}
        status = ""
        while status != "SUCCESS":
            response = requests.request("GET", url, headers=self.get_headers(), data=payload)
            submission_result = json.loads(response.text)
            status = submission_result["state"]
            time.sleep(1)

        print(f'Result: {submission_result["status_msg"]}')
        if submission_result["status_code"] == 10:
            print(
                f'Total Runtime: {submission_result["status_runtime"]} (Better than {submission_result["runtime_percentile"]:.2f}%)'
            )
            print(
                f'Total Memory: {submission_result["status_memory"]} (Better than {submission_result["memory_percentile"]:.2f}%)'
            )
        elif submission_result["status_code"] == 11:
            print(f'Last Input: {submission_result["input_formatted"]}')
            print(f'Expected Output: {submission_result["expected_output"]}')
            print(f'Code Output: {submission_result["code_output"]}')
        elif submission_result["status_code"] == 14:
            nl = "\n"
            print(f'Last Input: {submission_result["last_testcase"].replace(nl, " ")}')
            print(f'Expected Output: {submission_result["expected_output"]}')
            print(f'Code Output: {submission_result["code_output"]}')
        elif submission_result["status_code"] == 15:
            print(f'Runtime Error: {submission_result["runtime_error"]}')

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> Dict[str, Any]:
        """Get a list with 20 submissions

        Args:
            last_key (str, optional): the key of the last query. Defaults to "".
            offset (int, optional): the offset (used to query older values). Defaults to 0.

        Returns:
            Dict[str, Any]: the query response
        """
        url = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

        payload = {}

        response = requests.request("GET", url, headers=self.get_headers(), data=payload)

        return json.loads(response.text)

    def get_id_title_map(self) -> IdTitleMap:
        """Get a dictionary that maps the id to the question title slug

        Returns:
            IdTitleMap: maps the id to the title slug
        """
        url = "https://leetcode.com/api/problems/all/"

        payload = {}

        response = requests.request("GET", url, headers=self.get_headers(), data=payload)

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
