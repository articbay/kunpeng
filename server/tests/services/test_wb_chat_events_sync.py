from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


@pytest.mark.asyncio
async def test_sync_chat_events_paginates_filters_window_and_deduplicates():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 24, 10, 0, tzinfo=moscow)
    start_cursor = int(window_start.timestamp() * 1000)
    shop = Shop(
        id=7,
        name="WB",
        platform="wildberries",
        platform_shop_id="wb-7",
        api_key="token",
        user_id=1,
    )
    service = WBSyncService(AsyncMock(), shop)

    service.client = MagicMock()
    service.client.buyer_chat = MagicMock()
    service.client.buyer_chat.get_events = AsyncMock(
        side_effect=[
            {
                "result": {
                    "next": start_cursor + 1,
                    "totalEvents": 3,
                    "events": [
                        {
                            "eventID": "event-1",
                            "chatID": "chat-1",
                            "addTime": "2026-07-23T00:00:00",
                            "message": {"text": "first"},
                        },
                        {
                            "eventID": "too-old",
                            "chatID": "chat-2",
                            "addTime": "2026-07-22T23:59:59",
                        },
                        {
                            "eventID": "at-end",
                            "chatID": "chat-3",
                            "addTime": "2026-07-24T10:00:00",
                        },
                    ],
                }
            },
            {
                "result": {
                    "next": start_cursor + 2,
                    "totalEvents": 2,
                    "events": [
                        {
                            "eventID": "event-1",
                            "chatID": "chat-1",
                            "addTime": "2026-07-23T00:00:00",
                            "message": {"text": "updated"},
                        },
                        {
                            "eventID": "event-2",
                            "chatID": "chat-1",
                            "addTime": "2026-07-24T09:30:00",
                        },
                    ],
                }
            },
            {
                "result": {
                    "next": start_cursor + 2,
                    "totalEvents": 0,
                    "events": [],
                }
            },
        ]
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_chat_event"
    ) as chat_event_crud:
        chat_event_crud.upsert_many = AsyncMock(return_value=2)
        result = await service.sync_chat_events(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["scanned_count"] == 5
    assert service.client.buyer_chat.get_events.await_count == 3
    service.client.buyer_chat.get_events.assert_any_await(next_=start_cursor)

    events_data = chat_event_crud.upsert_many.await_args.kwargs["events_data"]
    events_by_id = {event["eventID"]: event for event in events_data}
    assert set(events_by_id) == {"event-1", "event-2"}
    assert events_by_id["event-1"]["message"]["text"] == "updated"


@pytest.mark.asyncio
async def test_sync_chat_events_rejects_non_advancing_cursor():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 24, 10, 0, tzinfo=moscow)
    cursor = int(window_start.timestamp() * 1000)
    shop = Shop(
        id=8,
        name="WB",
        platform="wildberries",
        platform_shop_id="wb-8",
        api_key="token",
        user_id=1,
    )
    service = WBSyncService(AsyncMock(), shop)
    service.client = MagicMock()
    service.client.buyer_chat = MagicMock()
    service.client.buyer_chat.get_events = AsyncMock(
        return_value={
            "result": {
                "next": cursor,
                "totalEvents": 1,
                "events": [],
            }
        }
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    result = await service.sync_chat_events(
        window_start=window_start,
        window_end=window_end,
    )

    assert result["status"] == "error"
    assert "cursor did not advance" in result["message"]
