from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


@pytest.mark.asyncio
async def test_sync_fbs_supplies_paginates_deduplicates_and_counts_window():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 24, 3, 0, tzinfo=moscow)
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
    service.client.marketplace = MagicMock()
    service.client.marketplace.get_supplies = AsyncMock(
        side_effect=[
            {
                "next": 20,
                "supplies": [
                    {
                        "id": "WB-GI-1",
                        "createdAt": "2026-07-23T08:00:00+03:00",
                    },
                    {
                        "id": "WB-GI-2",
                        "createdAt": "2026-07-20T08:00:00+03:00",
                    },
                ],
            },
            {
                "next": 20,
                "supplies": [
                    {
                        "id": "WB-GI-1",
                        "createdAt": "2026-07-23T08:00:00+03:00",
                    },
                    {
                        "id": "WB-GI-3",
                        "createdAt": "2026-07-20T08:00:00+03:00",
                        "closedAt": "2026-07-24T01:00:00+03:00",
                    },
                ],
            },
        ]
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_fbs_supply"
    ) as supply_crud:
        supply_crud.upsert_many = AsyncMock(side_effect=[2, 1])

        result = await service.sync_fbs_supplies(
            window_start=window_start,
            window_end=window_end,
        )

    assert result == {
        "status": "success",
        "message": "分页获取3张FBS供货单，写入3条，业务窗口内2条",
        "count": 3,
        "ods_count": 3,
        "window_count": 2,
        "page_count": 2,
    }
    assert service.client.marketplace.get_supplies.await_count == 2
    service.client.marketplace.get_supplies.assert_any_await(limit=1000, next_=0)
    service.client.marketplace.get_supplies.assert_any_await(limit=1000, next_=20)
    second_page = supply_crud.upsert_many.await_args_list[1].kwargs["supplies_data"]
    assert [supply["id"] for supply in second_page] == ["WB-GI-3"]
