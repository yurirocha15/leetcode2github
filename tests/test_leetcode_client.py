import asyncio
import json
from http.cookiejar import Cookie, CookieJar

import httpx
import pytest
from pydantic import BaseModel

from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeAuthError, LeetcodeClient


class DummyResponse(BaseModel):
    ok: bool


def cookie(name: str, value: str, domain: str) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=domain.startswith("."),
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def cookie_jar(*cookies: Cookie) -> CookieJar:
    jar = CookieJar()
    for cookie_item in cookies:
        jar.set_cookie(cookie_item)
    return jar


def make_client(handler):
    client = LeetcodeClient.__new__(LeetcodeClient)
    client.divider = "/"
    client.cookies = ""
    client.csrftoken = "csrf"
    client._transport = httpx.MockTransport(handler)
    client._timeout = 5.0
    return client


def question_response(
    *,
    content="<p>desc</p>",
    sample_test_case="[1]\n1",
    example_testcases="[1]\n1",
):
    return {
        "data": {
            "question": {
                "questionId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "content": content,
                "difficulty": "Easy",
                "exampleTestcases": example_testcases,
                "sampleTestCase": sample_test_case,
                "topicTags": [{"name": "Array", "slug": "array"}],
                "codeSnippets": [
                    {
                        "lang": "Python3",
                        "langSlug": "python3",
                        "code": "class Solution:\n    def twoSum(self):\n",
                    }
                ],
            }
        }
    }


def test_get_cookies_reads_chrome_session_and_host_only_csrf(monkeypatch):
    chrome_cookies = cookie_jar(
        cookie("LEETCODE_SESSION", "session", ".leetcode.com"),
        cookie("csrftoken", "csrf", "leetcode.com"),
        cookie("unrelated", "ignored", "example.com"),
    )

    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.chrome", lambda: chrome_cookies)
    monkeypatch.setattr(
        "leet2git.leetcode_client.browser_cookie3.firefox",
        lambda: pytest.fail("Firefox should not be used when Chrome has a session"),
    )

    client = LeetcodeClient()

    assert client.csrftoken == "csrf"
    assert "LEETCODE_SESSION=session" in client.cookies
    assert "csrftoken=csrf" in client.cookies
    assert "unrelated=ignored" not in client.cookies


def test_get_cookies_continues_after_browser_cookie_error(monkeypatch, capsys):
    firefox_cookies = cookie_jar(
        cookie("LEETCODE_SESSION", "firefox-session", ".leetcode.com"),
        cookie("csrftoken", "firefox-csrf", "leetcode.com"),
    )

    monkeypatch.setattr(
        "leet2git.leetcode_client.browser_cookie3.chrome",
        lambda: (_ for _ in ()).throw(
            __import__("browser_cookie3").BrowserCookieError("chrome unavailable")
        ),
    )
    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.firefox", lambda: firefox_cookies)

    client = LeetcodeClient()

    assert client.csrftoken == "firefox-csrf"
    assert "LEETCODE_SESSION=firefox-session" in client.cookies
    assert "chrome unavailable" in capsys.readouterr().out


def test_init_sets_windows_path_divider(monkeypatch):
    chrome_cookies = cookie_jar(cookie("LEETCODE_SESSION", "session", ".leetcode.com"))
    monkeypatch.setattr("leet2git.leetcode_client.platform.system", lambda: "Windows")
    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.chrome", lambda: chrome_cookies)
    monkeypatch.setattr(
        "leet2git.leetcode_client.browser_cookie3.firefox",
        lambda: pytest.fail("Firefox should not be used when Chrome has a session"),
    )

    client = LeetcodeClient()

    assert client.divider == "\\"


def test_get_cookies_requires_leetcode_session(monkeypatch):
    chrome_cookies = cookie_jar(cookie("csrftoken", "csrf", "leetcode.com"))
    firefox_cookies = cookie_jar()

    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.chrome", lambda: chrome_cookies)
    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.firefox", lambda: firefox_cookies)

    with pytest.raises(LeetcodeAuthError, match="Could not find a LeetCode login session"):
        LeetcodeClient()


def test_get_cookies_allows_missing_csrf_for_read_only_requests(monkeypatch):
    chrome_cookies = cookie_jar(cookie("LEETCODE_SESSION", "session", ".leetcode.com"))

    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.chrome", lambda: chrome_cookies)
    monkeypatch.setattr(
        "leet2git.leetcode_client.browser_cookie3.firefox",
        lambda: pytest.fail("Firefox should not be used when Chrome has a session"),
    )

    client = LeetcodeClient()

    assert client.csrftoken == ""
    assert "x-csrftoken" not in client.get_headers()


def test_get_cookies_uses_firefox_when_chrome_has_no_session(monkeypatch):
    chrome_cookies = cookie_jar(cookie("csrftoken", "stale", "leetcode.com"))
    firefox_cookies = cookie_jar(
        cookie("LEETCODE_SESSION", "firefox-session", ".leetcode.com"),
        cookie("csrftoken", "firefox-csrf", "leetcode.com"),
    )

    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.chrome", lambda: chrome_cookies)
    monkeypatch.setattr("leet2git.leetcode_client.browser_cookie3.firefox", lambda: firefox_cookies)

    client = LeetcodeClient()

    assert client.csrftoken == "firefox-csrf"
    assert "LEETCODE_SESSION=firefox-session" in client.cookies


def test_get_headers_include_cookie_and_conditional_csrf():
    client = LeetcodeClient.__new__(LeetcodeClient)
    client.cookies = "LEETCODE_SESSION=session; csrftoken=csrf"
    client.csrftoken = "csrf"

    headers = client.get_headers()

    assert headers["cookie"] == "LEETCODE_SESSION=session; csrftoken=csrf"
    assert headers["x-csrftoken"] == "csrf"
    assert headers["user-agent"]


def test_get_question_data_parses_description_examples_categories_and_raw_code():
    long_line = " ".join(["word"] * 30)
    content = (
        f"{long_line}\n"
        "x<sup>2</sup>\n"
        "Example 1:\n"
        "Input: nums = [2,7,11,15], target = 9\n"
        "Output: [0,1]\n"
        "Example 2:\n"
        "Input: nums = [3,2,4], target = 6\n"
        "Output\n"
        "[1,2]"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://leetcode.com/graphql"
        return httpx.Response(
            200,
            json=question_response(
                content=content,
                sample_test_case="[2,7,11,15]\n9",
                example_testcases="[2,7,11,15]\n9\n[3,2,4]\n6",
            ),
        )

    client = make_client(handler)

    data, is_new = client.get_question_data(1, "two-sum", "python3", "accepted code")

    assert is_new is True
    assert data.internal_id == 1
    assert data.title == "Two Sum"
    assert data.url == "https://leetcode.com/problems/two-sum"
    assert data.question_template.startswith("class Solution")
    assert data.categories[0].slug == "array"
    assert data.inputs == ["[2,7,11,15], 9", "[3,2,4], 6"]
    assert data.outputs == ["[0,1]", "[1,2]"]
    assert data.raw_code == "accepted code"
    assert data.file_path == "src/leetcode_1_two_sum"
    assert any("x^2" in line for line in data.description)
    assert all(len(line) <= 100 for line in data.description if line.startswith("word"))


def test_mutating_requests_require_csrf():
    client = make_client(lambda _: httpx.Response(500))
    client.cookies = "LEETCODE_SESSION=session"
    client.csrftoken = ""

    with pytest.raises(LeetcodeAuthError, match="csrftoken"):
        asyncio.run(
            client.async_submit_question(
                "class Solution: ...",
                1,
                "two-sum",
                "python3",
                is_test=True,
                test_input="[2,7,11,15]\n9",
            )
        )


def test_async_scrap_question_data_posts_current_graphql_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)

        assert request.method == "POST"
        assert str(request.url) == "https://leetcode.com/graphql"
        assert payload["operationName"] == "questionData"
        assert payload["variables"] == {"titleSlug": "two-sum"}

        return httpx.Response(
            200,
            json={
                "data": {
                    "question": {
                        "questionId": "1",
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "content": "<p>desc</p>",
                        "difficulty": "Easy",
                        "exampleTestcases": "[1]\n1",
                        "sampleTestCase": "[1]\n1",
                        "topicTags": [],
                        "codeSnippets": [
                            {
                                "langSlug": "python3",
                                "code": "class Solution:\n    def twoSum(self):\n",
                            }
                        ],
                    }
                }
            },
        )

    client = make_client(handler)

    response = asyncio.run(client.async_scrap_question_data("two-sum"))

    assert response.data.question
    assert response.data.question.question_id == "1"


def test_async_get_id_title_map_parses_problem_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://leetcode.com/api/problems/all/"
        return httpx.Response(
            200,
            json={
                "stat_status_pairs": [
                    {
                        "stat": {
                            "frontend_question_id": 1,
                            "question__title_slug": "two-sum",
                        }
                    }
                ]
            },
        )

    client = make_client(handler)

    id_title_map = asyncio.run(client.async_get_id_title_map())

    assert id_title_map.id_to_title == {1: "two-sum"}
    assert id_title_map.title_to_id == {"two-sum": 1}


def test_async_get_latest_submission_uses_submission_history():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if str(request.url) == "https://leetcode.com/api/problems/all/":
            return httpx.Response(
                200,
                json={
                    "stat_status_pairs": [
                        {
                            "stat": {
                                "frontend_question_id": 1,
                                "question__title_slug": "two-sum",
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "submissions_dump": [
                    {
                        "title_slug": "two-sum",
                        "status_display": "Accepted",
                        "lang": "python3",
                        "timestamp": 123,
                        "code": "class Solution: ...",
                    }
                ],
                "has_next": False,
                "last_key": "",
            },
        )

    client = make_client(handler)

    code = asyncio.run(client.async_get_latest_submission("1", "python3"))

    assert code == "class Solution: ..."
    assert requests == [
        "https://leetcode.com/api/problems/all/",
        "https://leetcode.com/api/submissions/?offset=0&limit=20&lastkey=",
    ]


def test_async_get_latest_submission_rejects_non_numeric_question_id():
    client = make_client(lambda _: httpx.Response(500))

    with pytest.raises(LeetcodeAPIError, match='Question id "abc" is not numeric'):
        asyncio.run(client.async_get_latest_submission("abc", "python3"))


def test_async_get_latest_submission_reports_missing_problem_id():
    client = make_client(lambda _: httpx.Response(200, json={"stat_status_pairs": []}))

    with pytest.raises(LeetcodeAPIError, match='did not include question "9999"'):
        asyncio.run(client.async_get_latest_submission("9999", "python3"))


def test_async_get_latest_submission_scans_paginated_history():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests.append(url)
        if url == "https://leetcode.com/api/problems/all/":
            return httpx.Response(
                200,
                json={
                    "stat_status_pairs": [
                        {
                            "stat": {
                                "frontend_question_id": 1,
                                "question__title_slug": "two-sum",
                            }
                        }
                    ]
                },
            )
        if "offset=0" in url:
            return httpx.Response(
                200,
                json={
                    "submissions_dump": [
                        {
                            "title_slug": "add-two-numbers",
                            "status_display": "Accepted",
                            "lang": "python3",
                            "timestamp": 123,
                            "code": "other code",
                        }
                    ],
                    "has_next": True,
                    "last_key": "next",
                },
            )
        return httpx.Response(
            200,
            json={
                "submissions_dump": [
                    {
                        "title_slug": "two-sum",
                        "status_display": "Accepted",
                        "lang": "python3",
                        "timestamp": 122,
                        "code": "target code",
                    }
                ],
                "has_next": False,
                "last_key": "",
            },
        )

    client = make_client(handler)

    assert asyncio.run(client.async_get_latest_submission("1", "python3")) == "target code"
    assert requests[-1] == "https://leetcode.com/api/submissions/?offset=20&limit=20&lastkey=next"


def test_get_latest_submission_reports_missing_history():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://leetcode.com/api/problems/all/":
            return httpx.Response(
                200,
                json={
                    "stat_status_pairs": [
                        {
                            "stat": {
                                "frontend_question_id": 1,
                                "question__title_slug": "two-sum",
                            }
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"submissions_dump": [], "has_next": False, "last_key": ""})

    client = make_client(handler)

    with pytest.raises(LeetcodeAPIError, match="Could not find"):
        client.get_latest_submission("1", "python3")


def test_async_submit_question_polls_until_success(monkeypatch):
    requests = []

    async def fake_sleep(delay: float) -> None:
        assert delay == 1

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))

        if request.method == "POST":
            payload = json.loads(request.content)
            assert payload["question_id"] == 1
            assert payload["judge_type"] == "large"
            return httpx.Response(200, json={"interpret_id": "runcode_123"})

        return httpx.Response(
            200,
            json={
                "state": "SUCCESS",
                "status_msg": "Accepted",
                "status_code": 10,
                "status_runtime": "1 ms",
                "status_memory": "1 MB",
                "code_output": ["[0,1]"],
            },
        )

    monkeypatch.setattr("leet2git.leetcode_client.asyncio.sleep", fake_sleep)
    client = make_client(handler)

    asyncio.run(
        client.async_submit_question(
            "class Solution: ...",
            1,
            "two-sum",
            "python3",
            is_test=True,
            test_input="[2,7,11,15]\n9",
        )
    )

    assert requests == [
        ("POST", "https://leetcode.com/problems/two-sum/interpret_solution/"),
        ("GET", "https://leetcode.com/submissions/detail/runcode_123/check/"),
    ]


@pytest.mark.parametrize(
    ("status_payload", "expected_output"),
    [
        (
            {
                "state": "SUCCESS",
                "status_msg": "Wrong Answer",
                "status_code": 11,
                "input_formatted": "[1,2]",
                "expected_output": "3",
                "code_output": "4",
            },
            ["Last Input: [1,2]", "Expected Output: 3", "Code Output: 4"],
        ),
        (
            {
                "state": "SUCCESS",
                "status_msg": "Time Limit Exceeded",
                "status_code": 14,
                "last_testcase": "[1,2]\n3",
                "expected_output": "3",
                "code_output": "timeout",
            },
            ["Last Input: [1,2] 3", "Expected Output: 3", "Code Output: timeout"],
        ),
        (
            {
                "state": "SUCCESS",
                "status_msg": "Runtime Error",
                "status_code": 15,
                "runtime_error": "IndexError",
            },
            ["Runtime Error: IndexError"],
        ),
        (
            {
                "state": "SUCCESS",
                "status_msg": "Compile Error",
                "status_code": 20,
                "compile_error": "SyntaxError",
            },
            ["Compile Error: SyntaxError"],
        ),
    ],
)
def test_async_submit_question_reports_non_accepted_result_shapes(
    monkeypatch,
    capsys,
    status_payload,
    expected_output,
):
    async def fake_sleep(delay: float) -> None:
        assert delay == 1

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"interpret_id": "runcode_123"})
        return httpx.Response(200, json=status_payload)

    monkeypatch.setattr("leet2git.leetcode_client.asyncio.sleep", fake_sleep)
    client = make_client(handler)

    asyncio.run(
        client.async_submit_question(
            "class Solution: ...",
            1,
            "two-sum",
            "python3",
            is_test=True,
            test_input="[1,2]",
        )
    )

    output = capsys.readouterr().out
    for expected in expected_output:
        assert expected in output


def test_async_submit_question_uses_real_submit_endpoint_and_percentiles(monkeypatch, capsys):
    requests = []

    async def fake_sleep(delay: float) -> None:
        assert delay == 1

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url), json.loads(request.content or b"{}")))
        if request.method == "POST":
            return httpx.Response(200, json={"submission_id": 456})
        return httpx.Response(
            200,
            json={
                "state": "SUCCESS",
                "status_msg": "Accepted",
                "status_code": 10,
                "status_runtime": "2 ms",
                "runtime_percentile": 98.765,
                "status_memory": "18 MB",
                "memory_percentile": 88.123,
            },
        )

    monkeypatch.setattr("leet2git.leetcode_client.asyncio.sleep", fake_sleep)
    client = make_client(handler)

    client.submit_question("class Solution: ...", 1, "two-sum", "python3")

    assert requests == [
        (
            "POST",
            "https://leetcode.com/problems/two-sum/submit/",
            {"question_id": 1, "lang": "python3", "typed_code": "class Solution: ..."},
        ),
        ("GET", "https://leetcode.com/submissions/detail/456/check/", {}),
    ]
    output = capsys.readouterr().out
    assert "Better than 98.77%" in output
    assert "Better than 88.12%" in output


def test_request_json_wraps_http_errors():
    client = make_client(lambda _: httpx.Response(403, json={"error": "forbidden"}))

    with pytest.raises(LeetcodeAPIError, match="HTTP 403"):
        asyncio.run(client._request_json("GET", "https://leetcode.com/api/private", DummyResponse))


def test_request_json_rejects_non_json_response():
    client = make_client(lambda _: httpx.Response(200, text="<html></html>"))

    with pytest.raises(LeetcodeAPIError, match="non-JSON"):
        asyncio.run(client._request_json("GET", "https://leetcode.com/api/private", DummyResponse))


def test_request_json_wraps_request_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    client = make_client(handler)

    with pytest.raises(LeetcodeAPIError, match="Could not reach LeetCode"):
        asyncio.run(client._request_json("GET", "https://leetcode.com/api/private", DummyResponse))


def test_sync_wrapper_closes_coroutines_inside_running_event_loop():
    client = make_client(lambda _: httpx.Response(200, json={}))

    class FakeCoroutine:
        closed = False

        def close(self):
            self.closed = True

    async def run_in_loop():
        fake_coroutine = FakeCoroutine()
        with pytest.raises(LeetcodeAPIError, match="active event loop"):
            client._run_async(fake_coroutine)
        return fake_coroutine

    fake_coroutine = asyncio.run(run_in_loop())

    assert fake_coroutine.closed is True


def test_submission_list_requires_expected_shape():
    client = make_client(lambda _: httpx.Response(200, json={"submissions_dump": []}))

    with pytest.raises(LeetcodeAPIError, match="has_next"):
        asyncio.run(client.async_get_submission_list())


def test_submission_list_retries_transient_403(monkeypatch):
    calls = 0
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(403, text="<html>Just a moment...</html>")
        return httpx.Response(
            200,
            json={"submissions_dump": [], "has_next": False, "last_key": ""},
        )

    monkeypatch.setattr("leet2git.leetcode_client.asyncio.sleep", fake_sleep)
    client = make_client(handler)

    response = asyncio.run(client.async_get_submission_list())

    assert response.has_next is False
    assert calls == 2
    assert sleeps == [5]


def test_get_question_data_validates_question_payload():
    client = make_client(lambda _: httpx.Response(200, json={"data": {"question": None}}))

    with pytest.raises(LeetcodeAPIError, match="two-sum"):
        client.get_question_data(1, "two-sum", "python3")


def test_get_question_data_requires_language_snippet():
    question_payload = {
        "data": {
            "question": {
                "questionId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
                "codeSnippets": [{"langSlug": "java", "code": "class Solution {}"}],
                "topicTags": [],
                "content": "<p>desc</p>",
                "sampleTestCase": "[1]\n1",
                "exampleTestcases": "[1]\n1",
            }
        }
    }
    client = make_client(lambda _: httpx.Response(200, json=question_payload))

    with pytest.raises(LeetcodeAPIError, match="python3"):
        client.get_question_data(1, "two-sum", "python3")
