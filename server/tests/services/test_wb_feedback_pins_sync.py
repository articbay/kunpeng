from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


def _service() -> WBSyncService:
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
    service.client.feedbacks = MagicMock()
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)
    return service


@pytest.mark.asyncio
async def test_sync_feedback_pins_paginates_and_deduplicates():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 25, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 26, 3, 0, tzinfo=moscow)
    service = _service()
    service.client.feedbacks.get_feedback_pins = AsyncMock(
        side_effect=[
            {
                "data": [
                    {
                        "pinId": 100,
                        "feedbackId": "feedback-1",
                        "state": "pinned",
                        "changeStateAt": "2026-07-25T10:00:00+03:00",
                    }
                ],
                "next": 100,
            },
            {
                "data": [
                    {
                        "pinId": 100,
                        "feedbackId": "feedback-1",
                        "state": "pinned",
                        "changeStateAt": "2026-07-25T11:00:00+03:00",
                    },
                ],
                "next": 0,
            },
            {
                "data": [
                    {
                        "pinId": 200,
                        "feedbackId": "feedback-2",
                        "state": "unpinned",
                        "changeStateAt": "2026-07-25T12:00:00+03:00",
                    },
                    {
                        "pinId": 300,
                        "feedbackId": "feedback-old",
                        "state": "unpinned",
                        "changeStateAt": "2026-07-24T12:00:00+03:00",
                    },
                ],
                "next": 0,
            },
        ]
    )

    with patch("kunpeng.services.wb_sync_service.crud_ods_wb_feedback_pin") as pin_crud:
        pin_crud.upsert_many = AsyncMock(return_value=2)
        result = await service.sync_feedback_pins(
            window_start=window_start,
            window_end=window_end,
        )

    assert result == {
        "status": "success",
        "message": "同步评价置顶及自动取消置顶记录2条，写入2条",
        "count": 2,
        "ods_count": 2,
        "page_count": 3,
    }
    assert service.client.feedbacks.get_feedback_pins.await_count == 3
    assert (
        service.client.feedbacks.get_feedback_pins.await_args_list[0].kwargs["state"]
        == "pinned"
    )
    assert (
        service.client.feedbacks.get_feedback_pins.await_args_list[-1].kwargs["state"]
        == "unpinned"
    )
    saved = pin_crud.upsert_many.await_args.kwargs["pins_data"]
    assert [item["pinId"] for item in saved] == [100, 200]
    assert saved[0]["state"] == "pinned"


@pytest.mark.asyncio
async def test_sync_feedback_pins_rolls_back_on_invalid_response():
    moscow = ZoneInfo("Europe/Moscow")
    service = _service()
    service.client.feedbacks.get_feedback_pins = AsyncMock(return_value={})

    with patch("kunpeng.services.wb_sync_service.crud_ods_wb_feedback_pin") as pin_crud:
        result = await service.sync_feedback_pins(
            window_start=datetime(2026, 7, 25, 0, 0, tzinfo=moscow),
            window_end=datetime(2026, 7, 26, 3, 0, tzinfo=moscow),
        )

    assert result["status"] == "error"
    pin_crud.upsert_many.assert_not_called()
    service.db.rollback.assert_awaited_once()
