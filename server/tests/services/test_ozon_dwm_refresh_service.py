from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.services import ozon_dwm_refresh_service as service_module
from kunpeng.services.ozon_dwm_refresh_service import OzonDWMRefreshService


def _crud_mock(*, source_bounds=(None, None), target_bounds=(None, None)):
    crud = Mock()
    crud.get_source_date_bounds = AsyncMock(return_value=source_bounds)
    crud.get_target_date_bounds = AsyncMock(return_value=target_bounds)
    crud.refresh_order_date_range = AsyncMock(
        return_value={"affected_rows": 2, "deleted_stale_rows": 0}
    )
    return crud


def test_chunk_range_uses_inclusive_thirty_day_segments() -> None:
    service = OzonDWMRefreshService()

    assert list(
        service._chunk_range(
            date(2026, 7, 1),
            date(2026, 8, 5),
            chunk_days=30,
        )
    ) == [
        (date(2026, 7, 1), date(2026, 7, 30)),
        (date(2026, 7, 31), date(2026, 8, 5)),
    ]


def test_consecutive_ranges_groups_only_adjacent_dates() -> None:
    service = OzonDWMRefreshService()

    assert service._consecutive_ranges(
        [date(2026, 7, 3), date(2026, 7, 1), date(2026, 7, 2), date(2026, 8, 1)]
    ) == [
        (date(2026, 7, 1), date(2026, 7, 3)),
        (date(2026, 8, 1), date(2026, 8, 1)),
    ]


@pytest.mark.asyncio
async def test_empty_target_is_backfilled_in_restart_safe_chunks() -> None:
    service = OzonDWMRefreshService()
    db = AsyncMock()
    crud = _crud_mock(
        source_bounds=(date(2026, 7, 1), date(2026, 8, 5)),
        target_bounds=(None, None),
    )

    result = await service._backfill_missing_coverage(db, crud=crud)

    assert result == {
        "range_count": 2,
        "affected_rows": 4,
        "deleted_stale_rows": 0,
    }
    assert crud.refresh_order_date_range.await_args_list[0].kwargs == {
        "date_from": date(2026, 7, 1),
        "date_to": date(2026, 7, 30),
    }
    assert crud.refresh_order_date_range.await_args_list[1].kwargs == {
        "date_from": date(2026, 7, 31),
        "date_to": date(2026, 8, 5),
    }
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_partial_target_resumes_after_existing_max_date() -> None:
    service = OzonDWMRefreshService()
    db = AsyncMock()
    crud = _crud_mock(
        source_bounds=(date(2026, 7, 1), date(2026, 8, 5)),
        target_bounds=(date(2026, 7, 1), date(2026, 7, 30)),
    )

    await service._backfill_missing_coverage(db, crud=crud)

    crud.refresh_order_date_range.assert_awaited_once_with(
        db,
        date_from=date(2026, 7, 31),
        date_to=date(2026, 8, 5),
    )


@pytest.mark.asyncio
async def test_refresh_all_covers_recent_days_and_late_return_order_dates() -> None:
    service = OzonDWMRefreshService()
    db = AsyncMock()
    goods = _crud_mock()
    lifecycle = _crud_mock()
    scope = Mock()
    scope.get_recent_return_order_dates = AsyncMock(
        return_value=[date(2026, 5, 10), date(2026, 8, 7)]
    )
    run_at = datetime(2026, 8, 10, 12, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(service_module, "crud_dwm_ozon_goods_trade_return_day", goods),
        patch.object(
            service_module,
            "crud_dwm_ozon_order_lifecycle_detail",
            lifecycle,
        ),
        patch.object(service_module, "crud_dwm_ozon_refresh_scope", scope),
    ):
        result = await service.refresh_all(db, run_at=run_at)

    for crud in (goods, lifecycle):
        assert crud.refresh_order_date_range.await_args_list[0].kwargs == {
            "date_from": date(2026, 8, 4),
            "date_to": date(2026, 8, 10),
        }
        assert crud.refresh_order_date_range.await_args_list[1].kwargs == {
            "date_from": date(2026, 5, 10),
            "date_to": date(2026, 5, 10),
        }
    assert result["historical_return_range_count"] == 1
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_refresh_all_rolls_back_current_range_on_failure() -> None:
    service = OzonDWMRefreshService()
    db = AsyncMock()
    goods = _crud_mock()
    lifecycle = _crud_mock()
    lifecycle.refresh_order_date_range.side_effect = RuntimeError("refresh failed")
    scope = Mock()
    scope.get_recent_return_order_dates = AsyncMock(return_value=[])
    run_at = datetime(2026, 8, 10, 12, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(service_module, "crud_dwm_ozon_goods_trade_return_day", goods),
        patch.object(
            service_module,
            "crud_dwm_ozon_order_lifecycle_detail",
            lifecycle,
        ),
        patch.object(service_module, "crud_dwm_ozon_refresh_scope", scope),
        pytest.raises(RuntimeError, match="refresh failed"),
    ):
        await service.refresh_all(db, run_at=run_at)

    db.rollback.assert_awaited_once()
