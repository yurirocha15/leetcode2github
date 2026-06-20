"""Read-only smoke check for LeetCode browser-cookie authentication."""

import asyncio
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from leet2git.leetcode_client import LeetcodeClient
from leet2git.leetcode_models import SubmissionListResponse


class UserStatus(BaseModel):
    """Authenticated user status returned by LeetCode globalData."""

    model_config = ConfigDict(populate_by_name=True)

    is_signed_in: bool = Field(alias="isSignedIn")
    username: str | None = None


class GlobalDataBody(BaseModel):
    """globalData GraphQL data field."""

    model_config = ConfigDict(populate_by_name=True)

    user_status: UserStatus = Field(alias="userStatus")


class GlobalDataResponse(BaseModel):
    """globalData GraphQL response."""

    data: GlobalDataBody


class EmptyVariables(BaseModel):
    """Empty GraphQL variables."""


class GlobalDataRequest(BaseModel):
    """globalData GraphQL request."""

    model_config = ConfigDict(populate_by_name=True)

    operation_name: Literal["globalData"] = Field(default="globalData", alias="operationName")
    variables: EmptyVariables = Field(default_factory=EmptyVariables)
    query: str = "query globalData { userStatus { isSignedIn username } }"


def print_mapping(name: str, value: Mapping[str, object]) -> None:
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
        GlobalDataResponse,
        json_body=GlobalDataRequest(),
    )
    status = user_status.data.user_status
    print_mapping(
        "user_status",
        {
            "keys": sorted(type(status).model_fields),
            "is_signed_in": status.is_signed_in,
            "username_present": bool(status.username),
        },
    )

    submissions = await client._request_json(
        "GET",
        "https://leetcode.com/api/submissions/?offset=0&limit=1&lastkey=",
        SubmissionListResponse,
    )
    print_mapping(
        "submissions",
        {
            "keys": sorted(type(submissions).model_fields),
            "submissions_dump_len": len(submissions.submissions_dump),
            "has_next_type": type(submissions.has_next).__name__,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
