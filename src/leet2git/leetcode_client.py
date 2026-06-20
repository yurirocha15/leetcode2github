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
from http.cookiejar import Cookie, CookieJar
from typing import Any

import browser_cookie3
import click
import httpx
from bs4 import BeautifulSoup

from leet2git.question_db import IdTitleMap, QuestionData

LEETCODE_COOKIE_DOMAINS = {"leetcode.com", ".leetcode.com"}
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


class LeetcodeAuthError(RuntimeError):
    """Raised when local browser cookies cannot authenticate with LeetCode."""


class LeetcodeAPIError(RuntimeError):
    """Raised when LeetCode returns an unexpected response or request failure."""


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
        browsers = (browser_cookie3.chrome, browser_cookie3.firefox)

        for browser in browsers:
            try:
                cookie_jar = browser()
            except browser_cookie3.BrowserCookieError as e:
                click.secho(e.args, fg="red")
                continue

            leetcode_cookies = self._get_leetcode_cookies(cookie_jar)
            if self._has_cookie(leetcode_cookies, "LEETCODE_SESSION"):
                return self._build_cookie_header(leetcode_cookies), self._get_cookie_value(
                    leetcode_cookies, "csrftoken"
                )

        raise LeetcodeAuthError(
            "Could not find a LeetCode login session in Chrome or Firefox. "
            "Log in to https://leetcode.com in a local browser and try again."
        )

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
            "user-agent": USER_AGENT,
            "cookie": self.cookies,
        }
        if self.csrftoken:
            headers["x-csrftoken"] = self.csrftoken

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
        question = self._get_question_payload(leetcode_question_data, title_slug)

        data = QuestionData(id=question_id, creation_time=time.time())
        data.internal_id = int(self._require_str(question, "questionId", "questionData.question"))
        data.title = self._require_str(question, "title", "questionData.question")
        data.title_slug = self._require_str(question, "titleSlug", "questionData.question")
        data.url = "https://leetcode.com/problems/" + data.title_slug
        data.difficulty = self._require_str(question, "difficulty", "questionData.question")
        data.question_template = self._get_code_snippet(question, language)
        data.categories = self._require_list(question, "topicTags", "questionData.question")

        # fix #24. 10<sup>5</sup> becomes 10^5
        soup = BeautifulSoup(
            re.sub(
                r"(?:\<sup\>)(\d+)(?:\<\/sup\>)",
                r"^\1",
                self._require_str(question, "content", "questionData.question"),
            ),
            features="html.parser",
        )
        data.description = soup.get_text().replace("\r\n", "\n").split("\n")
        sample_test_case = self._require_str(question, "sampleTestCase", "questionData.question")
        example_test_cases = self._require_str(question, "exampleTestcases", "questionData.question")
        num_of_inputs = len(sample_test_case.split("\n"))
        inputs = example_test_cases.split("\n")
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
            f"leetcode_{data.id}_" + data.title_slug.replace("-", "_"),
        )

        if code:
            data.raw_code = code

        return data, True

    def scrap_question_data(self, question_name: str) -> dict[str, Any]:
        """Query question information using the async HTTP implementation."""
        return self._run_async(self.async_scrap_question_data(question_name))

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
            raw_code = self._run_async(self.async_get_latest_submission(qid, language))
        except LeetcodeAPIError as e:
            click.secho(e.args, fg="red")
        return raw_code

    async def async_get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question asynchronously."""
        url: str = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"
        return self._require_str(await self._request_json("GET", url), "code", "latest submission")

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
        self._run_async(
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
        if not self.csrftoken:
            raise LeetcodeAuthError(
                "LeetCode did not expose a csrftoken cookie. Refusing to call a mutating "
                "submit/run endpoint because the current LeetCode auth flow may have changed."
            )
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
        submission_response = await self._request_json("POST", url, json_body=payload_dict)
        submission_id = self._require_int(submission_response, submission_field, "submit response")
        click.secho("Waiting for submission results...")
        url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"

        submission_result: dict[str, Any] = {}
        status: str = ""
        while status != "SUCCESS":
            submission_result = await self._request_json("GET", url)
            status = self._require_str(submission_result, "state", "submission status")
            await asyncio.sleep(1)

        click.clear()
        click.secho(f"Result: {submission_result.get('status_msg', 'Unknown')}")
        status_code = submission_result.get("status_code")
        if status_code == 10:
            click.secho(
                f"Total Runtime: {submission_result.get('status_runtime', 'unknown')} "
                + (
                    ""
                    if is_test
                    else f"(Better than {float(submission_result.get('runtime_percentile', 0)):.2f}%)"
                )
            )
            click.secho(
                f"Total Memory: {submission_result.get('status_memory', 'unknown')} "
                + (
                    ""
                    if is_test
                    else f"(Better than {float(submission_result.get('memory_percentile', 0)):.2f}%)"
                )
            )
        elif status_code == 11:
            click.secho(f"Last Input: {submission_result.get('input_formatted', 'unknown')}")
            click.secho(f"Expected Output: {submission_result.get('expected_output', 'unknown')}")
            click.secho(f"Code Output: {submission_result.get('code_output', 'unknown')}")
        elif status_code == 14:
            nl = "\n"
            last_testcase = str(submission_result.get("last_testcase", "unknown")).replace(nl, " ")
            click.secho(f"Last Input: {last_testcase}")
            click.secho(f"Expected Output: {submission_result.get('expected_output', 'unknown')}")
            click.secho(f"Code Output: {submission_result.get('code_output', 'unknown')}")
        elif status_code == 15:
            click.secho(f"Runtime Error: {submission_result.get('runtime_error', 'unknown')}")
        elif status_code == 20:
            click.secho(f"Compile Error: {submission_result.get('compile_error', 'unknown')}")

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> dict[str, Any]:
        """Get a list with 20 submissions using the async HTTP implementation."""
        return self._run_async(self.async_get_submission_list(last_key, offset))

    async def async_get_submission_list(self, last_key: str = "", offset: int = 0) -> dict[str, Any]:
        """Get a list with 20 submissions

        Args:
            last_key (str, optional): the key of the last query. Defaults to "".
            offset (int, optional): the offset (used to query older values). Defaults to 0.

        Returns:
            Dict[str, Any]: the query response
        """
        url: str = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

        response = await self._request_json("GET", url)
        self._require_list(response, "submissions_dump", "submission list")
        if not isinstance(response.get("has_next"), bool):
            raise LeetcodeAPIError(
                "LeetCode submission list response is missing boolean field has_next."
            )
        self._require_str(response, "last_key", "submission list")
        return response

    def get_id_title_map(self) -> IdTitleMap:
        """Get id/title mappings using the async HTTP implementation."""
        return self._run_async(self.async_get_id_title_map())

    async def async_get_id_title_map(self) -> IdTitleMap:
        """Get a dictionary that maps the id to the question title slug

        Returns:
            IdTitleMap: maps the id to the title slug
        """
        url: str = "https://leetcode.com/api/problems/all/"

        id_title_map: IdTitleMap = IdTitleMap()
        response = await self._request_json("GET", url)
        stat_status_pairs = self._require_list(response, "stat_status_pairs", "problem list")
        for stat in stat_status_pairs:
            if not isinstance(stat, dict) or not isinstance(stat.get("stat"), dict):
                continue
            stat_data = stat["stat"]
            frontend_id = stat_data.get("frontend_question_id")
            title_slug = stat_data.get("question__title_slug")
            if frontend_id is not None and isinstance(title_slug, str):
                id_title_map.id_to_title[int(frontend_id)] = title_slug
                id_title_map.title_to_id[title_slug] = int(frontend_id)

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
            try:
                response = await client.request(method, url, json=json_body)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as e:
                raise LeetcodeAPIError(
                    f"LeetCode request failed with HTTP {e.response.status_code}: {url}"
                ) from e
            except httpx.RequestError as e:
                raise LeetcodeAPIError(f"Could not reach LeetCode: {e}") from e
            except ValueError as e:
                raise LeetcodeAPIError(f"LeetCode returned a non-JSON response: {url}") from e

        if not isinstance(payload, dict):
            raise LeetcodeAPIError(f"LeetCode returned unexpected JSON for {url}")
        return payload

    def _run_async(self, coroutine: Any) -> Any:
        """Run an async client method from synchronous Click commands."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise LeetcodeAPIError("Cannot call synchronous LeetCode APIs from an active event loop.")

    def _get_question_payload(self, response: dict[str, Any], title_slug: str) -> dict[str, Any]:
        """Validate and return the question payload from GraphQL."""
        data = response.get("data")
        if not isinstance(data, dict):
            raise LeetcodeAPIError("LeetCode questionData response did not include data.")
        question = data.get("question")
        if not isinstance(question, dict):
            raise LeetcodeAPIError(f'LeetCode could not find question "{title_slug}".')
        return question

    def _get_code_snippet(self, question: dict[str, Any], language: str) -> str:
        """Return the LeetCode starter code for a language."""
        snippets = self._require_list(question, "codeSnippets", "questionData.question")
        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue
            if snippet.get("langSlug") == language and isinstance(snippet.get("code"), str):
                return snippet["code"]
        raise LeetcodeAPIError(f'LeetCode did not return a "{language}" code snippet.')

    def _require_str(self, payload: dict[str, Any], key: str, context: str) -> str:
        """Return a required string field from a LeetCode payload."""
        value = payload.get(key)
        if not isinstance(value, str):
            raise LeetcodeAPIError(f"LeetCode {context} response is missing string field {key}.")
        return value

    def _require_int(self, payload: dict[str, Any], key: str, context: str) -> int:
        """Return a required integer-like field from a LeetCode payload."""
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        raise LeetcodeAPIError(f"LeetCode {context} response is missing integer field {key}.")

    def _require_list(self, payload: dict[str, Any], key: str, context: str) -> list[Any]:
        """Return a required list field from a LeetCode payload."""
        value = payload.get(key)
        if not isinstance(value, list):
            raise LeetcodeAPIError(f"LeetCode {context} response is missing list field {key}.")
        return value

    def _get_leetcode_cookies(self, cookie_jar: CookieJar) -> list[Cookie]:
        """Return browser cookies scoped to LeetCode."""
        return [cookie for cookie in cookie_jar if cookie.domain in LEETCODE_COOKIE_DOMAINS]

    def _has_cookie(self, cookies: list[Cookie], name: str) -> bool:
        """Check whether a LeetCode cookie exists."""
        return any(cookie.name == name and bool(cookie.value) for cookie in cookies)

    def _get_cookie_value(self, cookies: list[Cookie], name: str) -> str:
        """Return a LeetCode cookie value without logging it."""
        for cookie in cookies:
            if cookie.name == name:
                return cookie.value or ""
        return ""

    def _build_cookie_header(self, cookies: list[Cookie]) -> str:
        """Build a Cookie header from browser cookies without a profile-page request."""
        return "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookies if cookie.value)


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848, "minimum-distance-to-the-target-element", "python"))
