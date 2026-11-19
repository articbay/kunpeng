"""Tests for the manual Wildberries DWD sync endpoint."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.api.v1 import wildberries


@pytest.mark.asyncio
async def test_manual_dwd_sync_returns_shop_stats(monkeypatch):
    db = AsyncMock()
    shop = Mock(id=8, platform="wildberries")
    get_shop = AsyncMock(return_value=shop)
    sync_dwd = AsyncMock(return_value={"scanned": 42, "created": 0, "updated": 42})
    monkeypatch.setattr(wildberries.shop_crud, "get", get_shop)
    monkeypatch.setattr(
        wildberries.wb_dwd_service,
        "sync_sales_report_detail",
        sync_dwd,
    )

    result = await wildberries.sync_sales_report_dwd_only(
        shop_id=8,
        db=db,
    )

    assert result == {
        "status": "success",
        "shop_id": 8,
        "scanned": 42,
        "created": 0,
        "updated": 42,
    }
    sync_dwd.assert_awaited_once_with(db, shop_id=8)


@pytest.mark.asyncio
async def test_manual_advert_dwd_sync_returns_four_results(monkeypatch):
    db = AsyncMock()
    shop = Mock(id=8, platform="wildberries")
    get_shop = AsyncMock(return_value=shop)
    dwd_results = {
        "activity_detail": {"created": 2},
        "bid_config": {"created": 3},
        "hourly_stats": {"created": 4},
        "daily_stats": {"created": 1},
    }
    sync_dwd = AsyncMock(return_value=dwd_results)
    monkeypatch.setattr(wildberries.shop_crud, "get", get_shop)
    monkeypatch.setattr(wildberries.wb_dwd_service, "sync_advert_all", sync_dwd)

    result = await wildberries.sync_advert_dwd_only(
        shop_id=8,
        date_from=date(2026, 8, 30),
        date_to=date(2026, 8, 31),
        db=db,
    )

    assert result == {
        "status": "success",
        "shop_id": 8,
        "date_from": "2026-08-30",
        "date_to": "2026-08-31",
        "results": dwd_results,
    }
    sync_dwd.assert_awaited_once_with(
        db,
        shop_id=8,
        date_from=date(2026, 8, 30),
        date_to=date(2026, 8, 31),
    )


@pytest.mark.asyncio
async def test_manual_funnel_dwd_sync_returns_shop_stats(monkeypatch):
    db = AsyncMock()
    shop = Mock(id=8, platform="wildberries")
    get_shop = AsyncMock(return_value=shop)
    sync_dwd = AsyncMock(return_value={"scanned": 245, "created": 0, "updated": 245})
    monkeypatch.setattr(wildberries.shop_crud, "get", get_shop)
    monkeypatch.setattr(
        wildberries.wb_dwd_service,
        "sync_sales_funnel_detail",
        sync_dwd,
    )

    result = await wildberries.sync_sales_funnel_dwd_only(
        shop_id=8,
        db=db,
    )

    assert result == {
        "status": "success",
        "shop_id": 8,
        "scanned": 245,
        "created": 0,
        "updated": 245,
    }
    sync_dwd.assert_awaited_once_with(db, shop_id=8)
