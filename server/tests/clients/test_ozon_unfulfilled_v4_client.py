from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.base import redact_headers
from kunpeng.clients.ozon import OzonPostingClient


@pytest.mark.asyncio
async def test_unfulfilled_v4_request_uses_cursor_and_root_contract():
    client = OzonPostingClient("client-id", "api-key")
    client._request = AsyncMock(
        return_value={
            "postings": [],
            "count": 0,
            "cursor": "",
            "has_next": False,
        }
    )

    await client.get_unfulfilled_postings(
        cutoff_from="2026-07-25T21:00:00.000Z",
        cutoff_to="2026-07-27T07:00:00.000Z",
        cursor="next-page",
        limit=100,
    )

    client._request.assert_awaited_once_with(
        "POST",
        "/v4/posting/fbs/unfulfilled/list",
        json={
            "dir": "ASC",
            "filter": {
                "cutoff_from": "2026-07-25T21:00:00.000Z",
                "cutoff_to": "2026-07-27T07:00:00.000Z",
            },
            "limit": 100,
            "cursor": "next-page",
            "with": {
                "analytics_data": True,
                "financial_data": True,
            },
        },
    )


def test_log_headers_are_redacted_case_insensitively():
    safe = redact_headers(
        {
            "Client-Id": "seller-client",
            "Api-Key": "seller-secret",
            "Authorization": "Bearer secret",
            "Content-Type": "application/json",
        }
    )

    assert safe == {
        "Client-Id": "***REDACTED***",
        "Api-Key": "***REDACTED***",
        "Authorization": "***REDACTED***",
        "Content-Type": "application/json",
    }
