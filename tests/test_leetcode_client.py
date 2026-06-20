import asyncio
import json
from http.cookiejar import Cookie, CookieJar

import httpx
import pytest

from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeAuthError, LeetcodeClient


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
                    }
                }
            },
        )

    client = make_client(handler)

    response = asyncio.run(client.async_scrap_question_data("two-sum"))

    assert response["data"]["question"]["questionId"] == "1"


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
            return httpx.Response(200, json={"interpret_id": 123})

        return httpx.Response(
            200,
            json={
                "state": "SUCCESS",
                "status_msg": "Accepted",
                "status_code": 10,
                "status_runtime": "1 ms",
                "status_memory": "1 MB",
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
        ("GET", "https://leetcode.com/submissions/detail/123/check/"),
    ]


def test_request_json_wraps_http_errors():
    client = make_client(lambda _: httpx.Response(403, json={"error": "forbidden"}))

    with pytest.raises(LeetcodeAPIError, match="HTTP 403"):
        asyncio.run(client._request_json("GET", "https://leetcode.com/api/private"))


def test_request_json_rejects_non_json_response():
    client = make_client(lambda _: httpx.Response(200, text="<html></html>"))

    with pytest.raises(LeetcodeAPIError, match="non-JSON"):
        asyncio.run(client._request_json("GET", "https://leetcode.com/api/private"))


def test_latest_submission_requires_code_field():
    client = make_client(lambda _: httpx.Response(200, json={}))

    with pytest.raises(LeetcodeAPIError, match="code"):
        asyncio.run(client.async_get_latest_submission("1", "python3"))


def test_submission_list_requires_expected_shape():
    client = make_client(lambda _: httpx.Response(200, json={"submissions_dump": []}))

    with pytest.raises(LeetcodeAPIError, match="has_next"):
        asyncio.run(client.async_get_submission_list())


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
