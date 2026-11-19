from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesBuyerChatClient


@pytest.mark.asyncio
async def test_buyer_chat_client_builds_events_cursor_query():
    client = WildberriesBuyerChatClient("token")
    client._request = AsyncMock(
        return_value={"result": {"events": [], "totalEvents": 0}}
    )

    await client.get_events(next_=1720000000123)

    client._request.assert_awaited_once_with(
        "GET",
        "/api/v1/seller/events",
        params={"next": 1720000000123},
    )


@pytest.mark.asyncio
async def test_buyer_chat_client_omits_optional_cursor():
    client = WildberriesBuyerChatClient("token")
    client._request = AsyncMock(
        return_value={"result": {"events": [], "totalEvents": 0}}
    )

    await client.get_events()

    client._request.assert_awaited_once_with(
        "GET",
        "/api/v1/seller/events",
        params=None,
    )
