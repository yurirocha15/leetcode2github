import asyncio
import json

import httpx

from leet2git.leetcode_client import LeetcodeClient


def make_client(handler):
    client = LeetcodeClient.__new__(LeetcodeClient)
    client.divider = "/"
    client.cookies = ""
    client.csrftoken = ""
    client._transport = httpx.MockTransport(handler)
    client._timeout = 5.0
    return client


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
