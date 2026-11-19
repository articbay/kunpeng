from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesFeedbacksClient


@pytest.mark.asyncio
async def test_feedbacks_client_gets_pins_by_state_and_cursor():
    client = WildberriesFeedbacksClient("token")
    client._request = AsyncMock(return_value={"data": [], "next": 0})

    await client.get_feedback_pins(
        state="unpinned",
        next_id=741,
        limit=500,
    )

    client._request.assert_awaited_once_with(
        "GET",
        "/api/feedbacks/v1/pins",
        params={
            "state": "unpinned",
            "limit": 500,
            "next": 741,
        },
    )


@pytest.mark.asyncio
async def test_feedbacks_client_rejects_invalid_pin_state():
    client = WildberriesFeedbacksClient("token")

    with pytest.raises(ValueError, match="state must"):
        await client.get_feedback_pins(state="all")
