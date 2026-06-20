"""
Handles the connection with github API
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import asyncio
import os
import platform
import textwrap
import time
from collections.abc import Coroutine
from http.cookiejar import Cookie, CookieJar
from typing import Any, TypeVar

import browser_cookie3
import click
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

from leet2git.leetcode_models import (
    InterpretSolutionResponse,
    LatestSubmissionResponse,
    ProblemListResponse,
    QuestionDataRequest,
    QuestionDataResponse,
    QuestionDataVariables,
    QuestionPayload,
    SubmissionListResponse,
    SubmissionResultResponse,
    SubmitSolutionPayload,
    SubmitSolutionResponse,
)
from leet2git.question_db import IdTitleMap, QuestionData

LEETCODE_COOKIE_DOMAINS = {"leetcode.com", ".leetcode.com"}
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


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
        data.internal_id = int(question.question_id)
        data.title = question.title
        data.title_slug = question.title_slug
        data.url = "https://leetcode.com/problems/" + data.title_slug
        data.difficulty = question.difficulty
        data.question_template = self._get_code_snippet(question, language)
        data.categories = question.topic_tags

        soup = BeautifulSoup(question.content, features="html.parser")
        for sup in soup.find_all("sup"):
            sup.string = "^" + sup.get_text()
        data.description = soup.get_text().replace("\r\n", "\n").split("\n")
        sample_test_case = question.sample_test_case
        example_test_cases = question.example_testcases
        num_of_inputs = len(sample_test_case.split("\n"))
        inputs = example_test_cases.split("\n")
        data.inputs = [
            ", ".join(inputs[i : i + num_of_inputs]) for i in range(0, len(inputs), num_of_inputs)
        ]
        tmp_description = []
        example_started = False
        for idx, line in enumerate(data.description):
            stripped_line = line.strip()
            if stripped_line.startswith("Example") and stripped_line.endswith(":"):
                example_started = True
            elif "Output: " in line and example_started:
                data.outputs.append(line[8:])
                example_started = False
            elif line == "Output" and example_started:
                data.outputs.append(data.description[idx + 1].strip())
                example_started = False
            if len(line) > 100:
                tmp_description.extend(textwrap.wrap(line, width=100, break_long_words=False))
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

    def scrap_question_data(self, question_name: str) -> QuestionDataResponse:
        """Query question information using the async HTTP implementation."""
        return self._run_async(self.async_scrap_question_data(question_name))

    async def async_scrap_question_data(self, question_name: str) -> QuestionDataResponse:
        """Query a question information

        Args:
            question_name (str): the question slug (which is inside the leetcode url)

        Returns:
            Dict[str, Dict[str, Any]]: the categories information
        """
        url: str = "https://leetcode.com/graphql"

        payload = QuestionDataRequest(
            variables=QuestionDataVariables(titleSlug=question_name),
            query="query questionData($titleSlug: String) {\n  question(titleSlug: $titleSlug) {\
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
        )

        return await self._request_json("POST", url, QuestionDataResponse, json_body=payload)

    def get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question

        Args:
            qid (str): the question id
            cookies (str): leetcode cookies
            language (str): the code language

        Returns:
            str: the submitted code
        """
        return self._run_async(self.async_get_latest_submission(qid, language))

    async def async_get_latest_submission(self, qid: str, language: str) -> str:
        """Get the latest submission for a question asynchronously."""
        url: str = f"https://leetcode.com/submissions/latest/?qid={qid}&lang={language}"
        response = await self._request_json("GET", url, LatestSubmissionResponse)
        return response.code

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

        payload = SubmitSolutionPayload(question_id=internal_id, lang=language, typed_code=code)
        if is_test:
            payload.data_input = test_input
            payload.judge_type = "large"

        if is_test:
            submission_response = await self._request_json(
                "POST",
                url,
                InterpretSolutionResponse,
                json_body=payload,
            )
            submission_id = submission_response.interpret_id
        else:
            submission_response = await self._request_json(
                "POST",
                url,
                SubmitSolutionResponse,
                json_body=payload,
            )
            submission_id = submission_response.submission_id
        click.secho("Waiting for submission results...")
        url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"

        submission_result: SubmissionResultResponse | None = None
        status: str = ""
        while status != "SUCCESS":
            submission_result = await self._request_json("GET", url, SubmissionResultResponse)
            status = submission_result.state
            await asyncio.sleep(1)

        if submission_result is None:
            raise LeetcodeAPIError("LeetCode did not return a submission result.")

        click.clear()
        click.secho(f"Result: {submission_result.status_msg or 'Unknown'}")
        status_code = submission_result.status_code
        if status_code == 10:
            click.secho(
                f"Total Runtime: {submission_result.status_runtime or 'unknown'} "
                + ("" if is_test else f"(Better than {submission_result.runtime_percentile or 0:.2f}%)")
            )
            click.secho(
                f"Total Memory: {submission_result.status_memory or 'unknown'} "
                + ("" if is_test else f"(Better than {submission_result.memory_percentile or 0:.2f}%)")
            )
        elif status_code == 11:
            click.secho(f"Last Input: {submission_result.input_formatted or 'unknown'}")
            click.secho(f"Expected Output: {submission_result.expected_output or 'unknown'}")
            click.secho(f"Code Output: {submission_result.code_output or 'unknown'}")
        elif status_code == 14:
            nl = "\n"
            last_testcase = (submission_result.last_testcase or "unknown").replace(nl, " ")
            click.secho(f"Last Input: {last_testcase}")
            click.secho(f"Expected Output: {submission_result.expected_output or 'unknown'}")
            click.secho(f"Code Output: {submission_result.code_output or 'unknown'}")
        elif status_code == 15:
            click.secho(f"Runtime Error: {submission_result.runtime_error or 'unknown'}")
        elif status_code == 20:
            click.secho(f"Compile Error: {submission_result.compile_error or 'unknown'}")

    def get_submission_list(self, last_key: str = "", offset: int = 0) -> SubmissionListResponse:
        """Get a list with 20 submissions using the async HTTP implementation."""
        return self._run_async(self.async_get_submission_list(last_key, offset))

    async def async_get_submission_list(
        self,
        last_key: str = "",
        offset: int = 0,
    ) -> SubmissionListResponse:
        """Get a list with 20 submissions

        Args:
            last_key (str, optional): the key of the last query. Defaults to "".
            offset (int, optional): the offset (used to query older values). Defaults to 0.

        Returns:
            Dict[str, Any]: the query response
        """
        url: str = f"https://leetcode.com/api/submissions/?offset={offset}&limit=20&lastkey={last_key}"

        return await self._request_json("GET", url, SubmissionListResponse)

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
        response = await self._request_json("GET", url, ProblemListResponse)
        for pair in response.stat_status_pairs:
            id_title_map.id_to_title[pair.stat.frontend_question_id] = pair.stat.question_title_slug
            id_title_map.title_to_id[pair.stat.question_title_slug] = pair.stat.frontend_question_id

        return id_title_map

    async def _request_json(
        self,
        method: str,
        url: str,
        model_type: type[ResponseModel],
        *,
        json_body: BaseModel | None = None,
    ) -> ResponseModel:
        """Send an authenticated LeetCode request and decode its JSON response."""
        async with httpx.AsyncClient(
            headers=self.get_headers(),
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=True,
        ) as client:
            try:
                body = (
                    json_body.model_dump(mode="json", by_alias=True, exclude_none=True)
                    if json_body
                    else None
                )
                response = await client.request(method, url, json=body)
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

        try:
            return model_type.model_validate(payload)
        except ValidationError as e:
            raise LeetcodeAPIError(f"LeetCode returned unexpected JSON for {url}: {e}") from e

    def _run_async(self, coroutine: Coroutine[Any, Any, Any]) -> Any:
        """Run an async client method from synchronous Click commands."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        coroutine.close()
        raise LeetcodeAPIError("Cannot call synchronous LeetCode APIs from an active event loop.")

    def _get_question_payload(
        self,
        response: QuestionDataResponse,
        title_slug: str,
    ) -> QuestionPayload:
        """Validate and return the question payload from GraphQL."""
        question = response.data.question
        if question is None:
            raise LeetcodeAPIError(f'LeetCode could not find question "{title_slug}".')
        return question

    def _get_code_snippet(self, question: QuestionPayload, language: str) -> str:
        """Return the LeetCode starter code for a language."""
        for snippet in question.code_snippets:
            if snippet.lang_slug == language:
                return snippet.code
        raise LeetcodeAPIError(f'LeetCode did not return a "{language}" code snippet.')

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
