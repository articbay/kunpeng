"""Tests for Wildberries advertising DWD orchestration."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from kunpeng.services import wb_dwd_service as service_module


@pytest.mark.asyncio
async def test_sync_advert_all_builds_hourly_before_daily(monkeypatch):
    service = service_module.WBDWDService()
    db = AsyncMock()
    call_order = []

    def builder(name):
        async def run(*_args, **_kwargs):
            call_order.append(name)
            return {"source_rows": 1, "created": 1, "updated": 0, "deleted": 0}

        return AsyncMock(side_effect=run)

    monkeypatch.setattr(
        service_module.crud_dwd_wb_advert_activity_detail,
        "refresh",
        builder("activity"),
    )
    monkeypatch.setattr(
        service_module.crud_dwd_wb_advert_bid_config,
        "refresh",
        builder("bid"),
    )
    monkeypatch.setattr(
        service_module.crud_dwd_wb_advert_stats_hourly_incr,
        "sync",
        builder("hourly"),
    )
    monkeypatch.setattr(
        service_module.crud_dwd_wb_advert_stats_daily_incr,
        "sync",
        builder("daily"),
    )

    result = await service.sync_advert_all(
        db,
        shop_id=8,
        snapshot_date=date(2026, 9, 1),
        date_from=date(2026, 8, 30),
        date_to=date(2026, 8, 31),
    )

    assert call_order == ["activity", "bid", "hourly", "daily"]
    assert set(result) == {
        "activity_detail",
        "bid_config",
        "hourly_stats",
        "daily_stats",
    }
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


def test_advert_stats_rejects_reversed_date_range():
    with pytest.raises(ValueError, match="date_from 不能晚于 date_to"):
        service_module.WBDWDService._validate_date_range(
            date(2026, 9, 1),
            date(2026, 8, 31),
        )
