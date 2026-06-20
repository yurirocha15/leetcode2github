"""
Handles the connection with github API
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import asyncio
import os
import platform
import re
import time
import traceback
from typing import Any

import browser_cookie3
import click
import httpx
import requests
from bs4 import BeautifulSoup

from leet2git.question_db import IdTitleMap, QuestionData


class LeetcodeClient:
    """Handles getting data from leetcode"""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ):
        os_name = platform.system()
        if os_name in ["Linux", "Darwin"]:
            self.divider = "/"
        elif os_name == "Windows":
            self.divider = "\\"

        self._transport = transport
        self._timeout = timeout
        self.cookies, self.csrftoken = self.get_cookies()

    def get_cookies(self) -> tuple[str, str]:
        """Get the cookies from the browser

        Returns:
            Tuple[str, str]: the raw cookies and the csrftoken
        """
        url: str = "https://leetcode.com/profile/"
        client = requests.session()
        browsers = (browser_cookie3.chrome, browser_cookie3.firefox)
        cookies = ""
        csrftoken = ""

        for browser in browsers:
            try:
                r = client.get(url, cookies=browser())
                cookies = str(r.request.headers["Cookie"])
                csrftoken = str(client.cookies["csrftoken"])
            except browser_cookie3.BrowserCookieError as e:
                click.secho(e.args, fg="red")
            if csrftoken:
                break

        return cookies, csrftoken

    def get_headers(self) -> dict[str, str]:
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
        self, question_id: int, title_slug: str, language: str, code: str | None = ""
    ) -> tuple[QuestionData, bool]:
        """Gets the data from a question

        Args:
            question_id (int): the question id
            title_slug (str): the question title
            language str: the language to download the code
            code (Optional[str]): the question solution

        Returns:
            QuestionData: The data needed to generate the question files
        """

        leetcode_question_data = self.scrap_question_data(title_slug)

        data = QuestionData(id=question_id, creation_time=time.time())
        data.internal_id = int(leetcode_question_data["data"]["question"]["questionId"])
        data.title = leetcode_question_data["data"]["question"]["title"]
        data.title_slug = leetcode_question_data["data"]["question"]["titleSlug"]
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

        # fix #24. 10<sup>5</sup> becomes 10^5
        soup = BeautifulSoup(
            re.sub(
                r"(?:\<sup\>)(\d+)(?:\<\/sup\>)",
                r"^\1",
                leetcode_question_data["data"]["question"]["content"],
            ),
            features="html.parser",
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
            f"leetcode_{data.id}_"
            + leetcode_question_data["data"]["question"]["titleSlug"].replace("-", "_"),
        )

        if code:
            data.raw_code = code

        return data, True

    def scrap_question_data(self, question_name: str) -> dict[str, Any]:
        """Query question information using the async HTTP implementation."""
        return asyncio.run(self.async_scrap_question_data(question_name))

    async def async_scrap_question_data(self, question_name: str) -> dict[str, Any]:
        """Query a question information

        Args:
            question_name (str): the question slug (which is inside the leetcode url)

        Returns:
            Dict[str, Dict[str, Any]]: the categories information
        """
        url: str = "https://leetcode.com/graphql"

        payload = {
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

        return await self._request_json("POST", url, json_body=payload)

    def get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question

        Args:
            qid (str): the question id
            cookies (str): leetcode cookies
            language (str): the code language

        Returns:
            str: the submitted code
        """
        raw_code: str = ""
        try:
            raw_code = asyncio.run(self.async_get_latest_submission(qid, language))
        except RuntimeError as e:
            click.secho(e.args, fg="red")
            click.secho(traceback.format_exc())
        return raw_code

    async def async_get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question asynchronously."""
        url: str = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"
        return (await self._request_json("GET", url))["code"]

    def submit_question(
        self,
        code: str,
        internal_id: int,
        title_slug: str,
        language: str,
        is_test: bool = False,
        test_input: str = "",
    ):
        """Submit question to Leetcode

        Args:
            code (str): the code which will be submitted
            internal_id (int): the question "questionId". (different from "frontend_id")
            title_slug (str): the question title slug
            language (str): the language of the code
            is_test (bool): if true, do not submit, only test on leetcode servers
            test_input (str): input to test. Only used if is_test is True
        """
        asyncio.run(
            self.async_submit_question(code, internal_id, title_slug, language, is_test, test_input)
        )

    async def async_submit_question(
        self,
        code: str,
        internal_id: int,
        title_slug: str,
        language: str,
        is_test: bool = False,
        test_input: str = "",
    ) -> None:
        """Submit or test a question asynchronously."""
        url: str = f"https://leetcode.com/problems/{title_slug}/" + (
            "interpret_solution/" if is_test else "submit/"
        )

        payload_dict: dict[str, Any] = {
            "question_id": internal_id,
            "lang": language,
            "typed_code": code,
        }
        if is_test:
            payload_dict["data_input"] = test_input
            payload_dict["judge_type"] = "large"

        submission_field: str = "interpret_id" if is_test else "submission_id"
        submission_id: int = (await self._request_json("POST", url, json_body=payload_dict))[
            submission_field
        ]
        click.secho("Waiting for submission results...")
        url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"

        status: str = ""
        while status != "SUCCESS":
            submission_result: dict[str, Any] = await self._request_json("GET", url)
            status = submission_result["state"]
            await asyncio.sleep(1)

        click.clear()
        click.secho(f"Result: {submission_result['status_msg']}")
        if submission_result["status_code"] == 10:
            click.secho(
                f"Total Runtime: {submission_result['status_runtime']} "
                + ("" if is_test else f"(Better than {submission_result['runtime_percentile']:.2f}%)")
            )
            click.secho(
                f"Total Memory: {submission_result['status_memory']} "
                + ("" if is_test else f"(Better than {submission_result['memory_percentile']:.2f}%)")
            )
        elif submission_result["status_code"] == 11:
            click.secho(f"Last Input: {submission_result['input_formatted']}")
            click.secho(f"Expected Output: {submission_result['expected_output']}")
            click.secho(f"Code Output: {submission_result['code_output']}")
        elif submission_result["status_code"] == 14:
            nl = "\n"
            click.secho(f"Last Input: {submission_result['last_testcase'].replace(nl, ' ')}")
            click.secho(f"Expected Output: {submission_result['expected_output']}")
            click.secho(f"Code Output: {submission_result['code_output']}")
        elif submission_result["status_code"] == 15:
            click.secho(f"Runtime Error: {submission_result['runtime_error']}")
        elif submission_result["status_code"] == 20:
            click.secho(f"Compile Error: {submission_result['compile_error']}")

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> dict[str, Any]:
        """Get a list with 20 submissions using the async HTTP implementation."""
        return asyncio.run(self.async_get_submission_list(last_key, offset))

    async def async_get_submission_list(self, last_key: str = "", offset: int = 0) -> dict[str, Any]:
        """Get a list with 20 submissions

        Args:
            last_key (str, optional): the key of the last query. Defaults to "".
            offset (int, optional): the offset (used to query older values). Defaults to 0.

        Returns:
            Dict[str, Any]: the query response
        """
        url: str = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

        return await self._request_json("GET", url)

    def get_id_title_map(self) -> IdTitleMap:
        """Get id/title mappings using the async HTTP implementation."""
        return asyncio.run(self.async_get_id_title_map())

    async def async_get_id_title_map(self) -> IdTitleMap:
        """Get a dictionary that maps the id to the question title slug

        Returns:
            IdTitleMap: maps the id to the title slug
        """
        url: str = "https://leetcode.com/api/problems/all/"

        id_title_map: IdTitleMap = IdTitleMap()
        response = await self._request_json("GET", url)
        for stat in response["stat_status_pairs"]:
            if "frontend_question_id" in stat["stat"] and "question__title_slug" in stat["stat"]:
                id_title_map.id_to_title[int(stat["stat"]["frontend_question_id"])] = stat["stat"][
                    "question__title_slug"
                ]
                id_title_map.title_to_id[stat["stat"]["question__title_slug"]] = int(
                    stat["stat"]["frontend_question_id"]
                )

        return id_title_map

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated LeetCode request and decode its JSON response."""
        async with httpx.AsyncClient(
            headers=self.get_headers(),
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=True,
        ) as client:
            response = await client.request(method, url, json=json_body)
            response.raise_for_status()
            return response.json()


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848, "minimum-distance-to-the-target-element", "python"))
