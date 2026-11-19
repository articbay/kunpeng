from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


@pytest.mark.asyncio
async def test_sync_order_metadata_uses_existing_orders_and_batches_by_100():
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

    async def metadata_response(order_ids):
        return {
            "orders": [
                {"id": order_id, "metaDetails": [], "meta": {}}
                for order_id in order_ids
            ]
        }

    service.client.marketplace.get_orders_metadata = AsyncMock(
        side_effect=metadata_response
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_order_metadata"
    ) as metadata_crud:
        metadata_crud.get_source_order_ids = AsyncMock(return_value=list(range(1, 202)))
        metadata_crud.upsert_many = AsyncMock(return_value=201)

        result = await service.sync_order_metadata(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["source_count"] == 201
    assert result["count"] == 201
    assert result["ods_count"] == 201
    assert result["batch_count"] == 3
    assert service.client.marketplace.get_orders_metadata.await_count == 3
    batch_sizes = [
        len(call.args[0])
        for call in service.client.marketplace.get_orders_metadata.await_args_list
    ]
    assert batch_sizes == [100, 100, 1]
    metadata_crud.get_source_order_ids.assert_awaited_once_with(
        service.db,
        shop_id=7,
        window_start=window_start,
        window_end=window_end,
    )
