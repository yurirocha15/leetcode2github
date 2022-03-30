"""
Handles the connection with github API
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import json
import os
import platform
import re
import time
import traceback
from typing import Any, Dict, Optional, Tuple

import browser_cookie3
import click
import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError
from requests.models import Response

from leet2git.data_schema import (
    LeetcodeAllProblems,
    LeetcodeQuestionData,
    LeetcodeSubmissionResult,
    SubmissionStatusCodes,
)
from leet2git.question_db import IdTitleMap, QuestionData

_TIMEOUT_TRIES_ = 20


class LeetcodeClient:
    """Handles getting data from leetcode"""

    def __init__(self):
        os_name = platform.system()
        if os_name in ["Linux", "Darwin"]:
            self.divider = "/"
        elif os_name == "Windows":
            self.divider = "\\"

        self.cookies, self.csrftoken = LeetcodeClient._get_cookies()

    def get_question_data(
        self, question_id: int, title_slug: str, language: str, code: Optional[str] = ""
    ) -> Tuple[QuestionData, bool]:
        """Gets the data from a question

        Args:
            question_id (int): the question id
            title_slug (str): the question title
            language str: the language to download the code
            code (Optional[str]): the question solution

        Returns:
            QuestionData: The data needed to generate the question files
        """
        try:
            leetcode_question_data = self._scrap_question_data(title_slug)
        except ValidationError as e:
            raise ValueError(f"Failed to get question {question_id} data") from e
        if not leetcode_question_data:
            raise ValueError(f"Failed to get question {question_id} data.")

        data = LeetcodeClient._build_question_data(leetcode_question_data, language, code)
        return data, True

    def get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question

        Args:
            qid (str): the question id
            cookies (str): leetcode cookies
            language (str): the code language

        Returns:
            str: the submitted code
        """
        url: str = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"

        payload: str = ""
        raw_code: str = ""
        try:
            response: Response = self._make_request("GET", url, payload)
            raw_code = json.loads(response.text)["code"]
        except RuntimeError as e:
            click.secho(e.args, fg="red")
            click.secho(traceback.format_exc())
        return raw_code

    def submit_question(
        self,
        code: str,
        internal_id: str,
        title_slug: str,
        language: str,
        is_test: bool = False,
        test_input: str = "",
    ):
        """Submit question to Leetcode

        Args:
            code (str): the code which will be submitted
            internal_id (str): the question "questionId". (different from "frontend_id")
            title_slug (str): the question title slug
            language (str): the language of the code
            is_test (bool): if true, do not submit, only test on leetcode servers
            test_input (str): input to test. Only used if is_test is True
        """

        url: str = f"https://leetcode.com/problems/{title_slug}/" + (
            "interpret_solution/" if is_test else "submit/"
        )

        payload_dict: Dict[str, str] = {
            "question_id": internal_id,
            "lang": language,
            "typed_code": code,
        }
        if is_test:
            payload_dict["data_input"] = test_input
            payload_dict["judge_type"] = "large"

        payload: str = json.dumps(payload_dict)
        response: Response = self._make_request("POST", url, payload)
        submission_field: str = "interpret_id" if is_test else "submission_id"
        submission_id: int = json.loads(response.text)[submission_field]
        click.secho("Waiting for submission results...")
        url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"

        payload = ""
        status: str = ""
        tries = 0
        while status != "SUCCESS" and tries < _TIMEOUT_TRIES_:
            response = self._make_request("GET", url, payload)
            raw_result: Dict[str, Any] = json.loads(response.text)
            if "state" in raw_result:
                status = raw_result["state"]
            tries += 1
            time.sleep(1)

        if tries >= _TIMEOUT_TRIES_:
            click.secho(f"Timed out after {tries} tries. Check url: {url}")
            return
        try:
            # for tests leetcode return an empty list instead of a string
            if is_test:
                raw_result.pop("code_output", "")
            submission_result = LeetcodeSubmissionResult(**raw_result)
        except ValidationError as e:
            raise ValueError("Failed to validate response data.") from e

        LeetcodeClient._process_submission_result(submission_result, is_test)

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> Dict[str, Any]:
        """Get a list with 20 submissions

        Args:
            last_key (str, optional): the key of the last query. Defaults to "".
            offset (int, optional): the offset (used to query older values). Defaults to 0.

        Returns:
            Dict[str, Any]: the query response
        """
        url: str = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

        payload: str = ""

        response: Response = self._make_request("GET", url, payload)

        return json.loads(response.text)

    def get_id_title_map(self) -> IdTitleMap:
        """Get a dictionary that maps the id to the question title slug

        Returns:
            IdTitleMap: maps the id to the title slug
        """
        url: str = "https://leetcode.com/api/problems/all/"

        payload: str = ""

        response: Response = self._make_request("GET", url, payload)

        id_title_map: IdTitleMap = IdTitleMap()
        raw_data = json.loads(response.text)
        try:
            all_problems = LeetcodeAllProblems(**raw_data)
        except ValidationError as e:
            raise ValueError("Failed to parse question data.") from e
        for stat in all_problems.stat_status_pairs:
            id_title_map.id_to_title[
                int(stat.stat.frontend_question_id)
            ] = stat.stat.question__title_slug
            id_title_map.title_to_id[stat.stat.question__title_slug] = int(
                stat.stat.frontend_question_id
            )

        return id_title_map

    def _scrap_question_data(self, question_name: str) -> Optional[LeetcodeQuestionData]:
        """Query a question information

        Args:
            question_name (str): the question slug (which is inside the leetcode url)

        Returns:
            Optional[LeetcodeQuestionData]: the question information
        """
        url: str = "https://leetcode.com/graphql"

        payload: str = json.dumps(
            {
                "operationName": "questionData",
                "variables": {"titleSlug": question_name},
                "query": "query questionData($titleSlug: String) {\n  question(titleSlug: $titleSlug) {\
                    \n    questionId\
                    \n    questionFrontendId\
                    \n    title\
                    \n    titleSlug\
                    \n    content\
                    \n    isPaidOnly\
                    \n    difficulty\
                    \n    likes\
                    \n    dislikes\
                    \n    exampleTestcases\
                    \n    topicTags {\
                    \n      name\
                    \n      slug\
                    \n      translatedName\
                    \n      __typename\
                    \n    }\
                    \n    codeSnippets {\
                    \n      lang\
                    \n      langSlug\
                    \n      code\
                    \n      __typename\
                    \n    }\
                    \n    stats\
                    \n    hints\
                    \n    solution {\
                    \n      id\
                    \n      canSeeDetail\
                    \n      paidOnly\
                    \n      hasVideoSolution\
                    \n      paidOnlyVideo\
                    \n      __typename\
                    \n    }\
                    \n    status\
                    \n    sampleTestCase\
                    \n    metaData\
                    \n    __typename\n  }\n}\n",
            }
        )

        response: Response = self._make_request("POST", url, payload)
        question_data = json.loads(response.text)
        if "data" not in question_data or "question" not in question_data["data"]:
            return None
        return LeetcodeQuestionData(**question_data["data"]["question"])

    def _get_headers(self) -> Dict[str, str]:
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

    def _make_request(self, method: str, url: str, payload: str) -> Response:
        """Makes a request

        Args:
            method (str): Either GET or POST
            url (str): the request url
            payload (str): the request payload

        Returns:
            Response: the request response
        """
        return requests.request(method, url, headers=self._get_headers(), data=payload)

    @staticmethod
    def _get_cookies() -> Tuple[str, str]:
        """Get the cookies from the browser

        Returns:
            Tuple[str, str]: the raw cookies and the csrftoken
        """
        url: str = "https://leetcode.com/profile/"
        client = requests.session()
        browsers = (browser_cookie3.chrome, browser_cookie3.firefox)

        for browser in browsers:
            try:
                r = client.get(url, cookies=browser())
                cookies = r.request.headers["Cookie"]
                csrftoken = client.cookies["csrftoken"]
            except browser_cookie3.BrowserCookieError as e:
                click.secho(e.args, fg="red")
            if csrftoken:
                break

        return cookies, csrftoken

    @staticmethod
    def _build_question_data(
        leetcode_question_data: LeetcodeQuestionData, language: str, code: Optional[str] = ""
    ) -> QuestionData:
        """Converts the response from leetcode to QuestionData object

        Args:
            leetcode_question_data (LeetcodeQuestionData): the leetcode response data

        Returns:
            QuestionData: the formated question data
        """
        data = QuestionData(id=leetcode_question_data.questionFrontendId, creation_time=time.time())
        data.internal_id = int(leetcode_question_data.questionId)
        data.title = leetcode_question_data.title
        data.title_slug = leetcode_question_data.titleSlug
        data.url = "https://leetcode.com/problems/" + leetcode_question_data.titleSlug
        data.difficulty = leetcode_question_data.difficulty
        data.question_template = next(
            code.code for code in leetcode_question_data.codeSnippets if code.langSlug == language
        )
        data.categories = leetcode_question_data.topicTags

        # fix #24. 10<sup>5</sup> becomes 10^5
        soup = BeautifulSoup(
            re.sub(
                r"(?:\<sup\>)(\d+)(?:\<\/sup\>)",
                r"^\1",
                leetcode_question_data.content,
            ),
            features="html.parser",
        )
        data.description = soup.get_text().replace("\r\n", "\n").split("\n")
        num_of_inputs = len(leetcode_question_data.sampleTestCase.split("\n"))
        inputs = leetcode_question_data.exampleTestcases.split("\n")
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
                    if not tmp_line or len(tmp_line) + len(phrase) <= 100:
                        tmp_line += phrase
                    else:
                        tmp_description.append(tmp_line)
                        tmp_line = phrase
                if tmp_line:
                    tmp_description.append(tmp_line)
            else:
                tmp_description.append(line)
        data.description = tmp_description

        data.file_path = os.path.join(
            "src",
            f"leetcode_{data.id}_" + leetcode_question_data.titleSlug.replace("-", "_"),
        )

        if code:
            data.raw_code = code

        return data

    @staticmethod
    def _process_submission_result(submission_result: LeetcodeSubmissionResult, is_test: bool):
        """Print submission result to terminal

        Args:
            submission_result (LeetcodeSubmissionResult): the submission result
        """

        click.clear()
        click.secho(f"Result: {submission_result.status_msg}")
        # success
        if submission_result.status_code == SubmissionStatusCodes.SUCCESS:
            click.secho(
                f"Total Runtime: {submission_result.status_runtime} "
                + ("" if is_test else f"(Better than {submission_result.runtime_percentile:.2f}%)")
            )
            click.secho(
                f"Total Memory: {submission_result.status_memory} "
                + ("" if is_test else f"(Better than {submission_result.memory_percentile:.2f}%)")
            )
        # Wrong Answer
        elif submission_result.status_code == SubmissionStatusCodes.WRONG_ANSWER:
            click.secho(f"Last Input: {submission_result.input_formatted}")
            click.secho(f"Expected Output: {submission_result.expected_output}")
            click.secho(f"Code Output: {submission_result.code_output}")
        # Time Limit Exceeded
        elif submission_result.status_code == SubmissionStatusCodes.TIME_LIMIT_EXCEEDED:
            nl = "\n"
            click.secho(f'Last Input: {submission_result.last_testcase.replace(nl, " ")}')
            click.secho(f"Expected Output: {submission_result.expected_output}")
            click.secho(f"Code Output: {submission_result.code_output}")
        # Runtime Error
        elif submission_result.status_code == SubmissionStatusCodes.RUNTIME_ERROR:
            click.secho(f"Runtime Error: {submission_result.runtime_error}")
        # Compile Error
        elif submission_result.status_code == SubmissionStatusCodes.COMPILE_ERROR:
            click.secho(f"Compile Error: {submission_result.compile_error}")
        # TODO: MISSING CASES
        # 12: return 'Memory Limit Exceeded';
        # 13: return 'Output Limit Exceeded';
        # 21: return 'Unknown Error';


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848, "minimum-distance-to-the-target-element", "python"))
