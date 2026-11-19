from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.services import wb_dwm_refresh_service as service_module
from kunpeng.services.wb_dwm_refresh_service import WBDWMRefreshService


def test_chunk_range_uses_inclusive_segments():
    assert list(
        WBDWMRefreshService._chunk_range(
            date(2026, 7, 1),
            date(2026, 8, 5),
            chunk_days=30,
        )
    ) == [
        (date(2026, 7, 1), date(2026, 7, 30)),
        (date(2026, 7, 31), date(2026, 8, 5)),
    ]


@pytest.mark.asyncio
async def test_backfill_all_refreshes_complete_source_range():
    service = WBDWMRefreshService()
    db = AsyncMock()
    crud = AsyncMock()
    crud.get_source_date_bounds.return_value = (
        date(2026, 7, 1),
        date(2026, 8, 5),
    )
    crud.refresh_date_range.return_value = {
        "affected_rows": 4,
        "deleted_stale_rows": 0,
        "unattributed_order_rows": 1,
        "unattributed_return_rows": 2,
    }

    with patch.object(service_module, "crud_dwm_wb_goods_oper_day", crud):
        result = await service.backfill_all(db, shop_id=8)

    assert result["range_count"] == 2
    assert result["affected_rows"] == 8
    assert crud.refresh_date_range.await_args_list[0].kwargs == {
        "date_from": date(2026, 7, 1),
        "date_to": date(2026, 7, 30),
        "shop_id": 8,
    }
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_refresh_range_rolls_back_on_failure():
    service = WBDWMRefreshService()
    db = AsyncMock()
    crud = AsyncMock()
    crud.refresh_date_range.side_effect = RuntimeError("failed")
    with (
        patch.object(service_module, "crud_dwm_wb_goods_oper_day", crud),
        pytest.raises(RuntimeError, match="failed"),
    ):
        await service.refresh_range(
            db,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 2),
        )
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_lifecycle_all_refreshes_complete_source_range():
    service = WBDWMRefreshService()
    db = AsyncMock()
    crud = AsyncMock()
    crud.get_source_date_bounds.return_value = (
        date(2026, 7, 1),
        date(2026, 8, 5),
    )
    crud.refresh_order_date_range.return_value = {
        "affected_rows": 5,
        "deleted_stale_rows": 0,
        "unmatched_return_rows": 1,
        "ambiguous_return_rows": 0,
        "marketplace_missing_srid_rows": 0,
    }

    with patch.object(
        service_module,
        "crud_dwm_wb_order_lifecycle_detail",
        crud,
    ):
        result = await service.backfill_lifecycle_all(db, shop_id=8)

    assert result["range_count"] == 2
    assert result["affected_rows"] == 10
    assert result["unmatched_return_rows"] == 2
    assert crud.refresh_order_date_range.await_args_list[0].kwargs == {
        "date_from": date(2026, 7, 1),
        "date_to": date(2026, 7, 30),
        "shop_id": 8,
    }
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_refresh_lifecycle_all_refreshes_recent_and_historical_returns():
    service = WBDWMRefreshService()
    db = AsyncMock()
    crud = AsyncMock()
    crud.get_source_date_bounds.return_value = (
        date(2026, 1, 1),
        date(2026, 8, 31),
    )
    crud.get_target_date_bounds.return_value = (
        date(2026, 1, 1),
        date(2026, 8, 31),
    )
    crud.get_return_order_dates.return_value = [
        date(2026, 1, 10),
        date(2026, 1, 11),
        date(2026, 1, 13),
        date(2026, 8, 1),
    ]
    crud.refresh_order_date_range.return_value = {
        "affected_rows": 1,
        "deleted_stale_rows": 0,
        "unmatched_return_rows": 0,
        "ambiguous_return_rows": 0,
        "marketplace_missing_srid_rows": 0,
    }

    with patch.object(
        service_module,
        "crud_dwm_wb_order_lifecycle_detail",
        crud,
    ):
        result = await service.refresh_lifecycle_all(
            db,
            run_at=datetime(
                2026,
                9,
                1,
                tzinfo=ZoneInfo("Europe/Moscow"),
            ),
        )

    assert result["backfill"]["range_count"] == 0
    assert result["recent"]["date_from"] == "2026-06-04"
    assert result["recent"]["date_to"] == "2026-08-31"
    assert result["historical_return_range_count"] == 2
    assert crud.refresh_order_date_range.await_count == 3
    assert crud.refresh_order_date_range.await_args_list[1].kwargs == {
        "date_from": date(2026, 1, 10),
        "date_to": date(2026, 1, 11),
        "shop_id": None,
    }
