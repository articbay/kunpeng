"""Wildberries 销售漏斗手动同步入口测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from kunpeng.api.v1.wildberries import sync_funnel_only


@pytest.mark.asyncio
@patch("kunpeng.api.v1.wildberries.WBSyncService")
@patch("kunpeng.api.v1.wildberries.shop_crud.get", new_callable=AsyncMock)
async def test_manual_funnel_sync_without_dates_uses_lookback(
    mock_get_shop, mock_service_class
):
    mock_get_shop.return_value = Mock(id=1)
    service = mock_service_class.return_value
    service.sync_funnel_lookback = AsyncMock(
        return_value={
            "status": "success",
            "message": "销售漏斗 T-7 至 T-1 回补完成",
            "count": 7,
        }
    )

    response = await sync_funnel_only(
        shop_id=1,
        date_from=None,
        date_to=None,
        db=AsyncMock(),
    )

    service.sync_funnel_lookback.assert_awaited_once_with()
    service.sync_funnel.assert_not_called()
    assert response.data["count"] == 7


@pytest.mark.asyncio
@patch("kunpeng.api.v1.wildberries.WBSyncService")
@patch("kunpeng.api.v1.wildberries.shop_crud.get", new_callable=AsyncMock)
async def test_manual_funnel_sync_with_dates_keeps_requested_window(
    mock_get_shop, mock_service_class
):
    mock_get_shop.return_value = Mock(id=1)
    service = mock_service_class.return_value
    service.sync_funnel = AsyncMock(
        return_value={
            "status": "success",
            "message": "指定区间同步完成",
            "count": 1,
        }
    )

    await sync_funnel_only(
        shop_id=1,
        date_from="2026-07-29",
        date_to="2026-07-29",
        db=AsyncMock(),
    )

    service.sync_funnel.assert_awaited_once_with("2026-07-29", "2026-07-29")
    service.sync_funnel_lookback.assert_not_called()
