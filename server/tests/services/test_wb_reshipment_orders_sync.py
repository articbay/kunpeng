from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


def _service():
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
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)
    return service


@pytest.mark.asyncio
async def test_sync_reshipment_orders_reconciles_valid_snapshot():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 24, 3, 0, tzinfo=moscow)
    service = _service()
    orders = [{"orderID": 123, "supplyID": "WB-GI-1"}]
    service.client.marketplace.get_reshipment_orders = AsyncMock(
        return_value={"orders": orders}
    )

    with patch("kunpeng.services.wb_sync_service.crud_ods_wb_reshipment_order") as crud:
        crud.reconcile_snapshot = AsyncMock(
            return_value={
                "count": 1,
                "ods_count": 1,
                "new_count": 1,
                "reactivated_count": 0,
                "resolved_count": 0,
            }
        )
        crud.count_changed_in_window = AsyncMock(return_value=1)

        result = await service.sync_reshipment_orders(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["new_count"] == 1
    assert result["window_count"] == 1
    crud.reconcile_snapshot.assert_awaited_once_with(
        service.db,
        orders_data=orders,
        shop_id=7,
        observed_at=window_end,
    )


@pytest.mark.asyncio
async def test_sync_reshipment_orders_does_not_reconcile_invalid_response():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 0, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 24, 3, 0, tzinfo=moscow)
    service = _service()
    service.client.marketplace.get_reshipment_orders = AsyncMock(
        return_value={"unexpected": []}
    )

    with patch("kunpeng.services.wb_sync_service.crud_ods_wb_reshipment_order") as crud:
        result = await service.sync_reshipment_orders(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "error"
    crud.reconcile_snapshot.assert_not_called()
    service.db.rollback.assert_awaited_once()
