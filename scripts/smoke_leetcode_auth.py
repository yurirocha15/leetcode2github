"""Read-only smoke check for LeetCode browser-cookie authentication."""

import asyncio
from typing import Any

from leet2git.leetcode_client import LeetcodeClient


def print_mapping(name: str, value: dict[str, Any]) -> None:
    """Print small redacted dictionaries for manual smoke output."""
    print(f"{name}:")
    for key, item in value.items():
        print(f"  {key}: {item}")


async def main() -> None:
    client = LeetcodeClient(timeout=20.0)
    cookie_names = sorted(
        cookie_pair.split("=", 1)[0] for cookie_pair in client.cookies.split("; ") if cookie_pair
    )

    print_mapping(
        "cookie_discovery",
        {
            "cookie_names": cookie_names,
            "leetcode_session_present": "LEETCODE_SESSION" in cookie_names,
            "csrftoken_present": bool(client.csrftoken),
        },
    )

    user_status = await client._request_json(
        "POST",
        "https://leetcode.com/graphql",
        json_body={
            "operationName": "globalData",
            "variables": {},
            "query": "query globalData { userStatus { isSignedIn username } }",
        },
    )
    status = user_status.get("data", {}).get("userStatus", {})
    print_mapping(
        "user_status",
        {
            "keys": sorted(status),
            "is_signed_in": status.get("isSignedIn"),
            "username_present": bool(status.get("username")),
        },
    )

    submissions = await client._request_json(
        "GET", "https://leetcode.com/api/submissions/?offset=0&limit=1&lastkey="
    )
    print_mapping(
        "submissions",
        {
            "keys": sorted(submissions),
            "submissions_dump_len": len(submissions.get("submissions_dump", [])),
            "has_next_type": type(submissions.get("has_next")).__name__,
        },
    )

    latest_submission = await client.async_get_latest_submission("1", "python3")
    print_mapping(
        "latest_submission",
        {
            "code_present": bool(latest_submission),
            "code_length": len(latest_submission),
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
