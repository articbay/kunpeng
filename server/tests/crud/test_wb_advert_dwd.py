"""Tests for the four Wildberries advertising DWD builders."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.advert import _merge_daily_fact_groups, _sum_metrics
from kunpeng.crud.ods.wildberries.advert_product import crud_ods_wb_advert_product
from kunpeng.models.dwd.wildberries.advert import (
    DWDWBAdvertActivityDetail,
    DWDWBAdvertBidConfig,
    DWDWBAdvertStatsDailyIncr,
    DWDWBAdvertStatsHourlyIncr,
)


def test_advert_dwd_models_keep_original_currency_without_cny_fields():
    models = (
        DWDWBAdvertActivityDetail,
        DWDWBAdvertBidConfig,
        DWDWBAdvertStatsHourlyIncr,
        DWDWBAdvertStatsDailyIncr,
    )

    for model in models:
        column_names = set(model.__table__.columns.keys())
        assert "currency" in column_names
        assert not any("cny" in name.lower() for name in column_names)


def test_hourly_metric_rollup_sums_raw_amounts_and_recalculates_ratios():
    rows = [
        SimpleNamespace(
            views=100,
            clicks=10,
            atbs=4,
            orders=2,
            canceled=0,
            shks=2,
            sum_cost=Decimal("25.50"),
            sum_price=Decimal("80.00"),
        ),
        SimpleNamespace(
            views=50,
            clicks=5,
            atbs=1,
            orders=1,
            canceled=1,
            shks=1,
            sum_cost=Decimal("14.50"),
            sum_price=Decimal("40.00"),
        ),
    ]

    result = _sum_metrics(rows)

    assert result["views"] == 150
    assert result["clicks"] == 15
    assert result["sum_cost"] == Decimal("40.00")
    assert result["sum_price"] == Decimal("120.00")
    assert result["cpc"] == Decimal("2.666667")
    assert result["ctr"] == Decimal("0.1")
    assert result["cr"] == Decimal("0.2")
    assert result["roi"] == Decimal("3")


def test_daily_rollup_prefers_fullstats_and_keeps_hourly_fallback():
    shared_key = {
        "stat_date": date(2026, 8, 10),
        "advert_id": 10,
        "nm_id": 20,
        "currency": "CNY",
    }
    hourly_shared = SimpleNamespace(**shared_key, clicks=2)
    hourly_only = SimpleNamespace(
        stat_date=date(2026, 8, 11),
        advert_id=10,
        nm_id=20,
        currency="CNY",
        clicks=3,
    )
    full_mobile = SimpleNamespace(**shared_key, clicks=5)
    full_desktop = SimpleNamespace(**shared_key, clicks=7)

    grouped = _merge_daily_fact_groups(
        [hourly_shared, hourly_only],
        [full_mobile, full_desktop],
    )

    shared = grouped[(date(2026, 8, 10), 10, 20, "CNY")]
    fallback = grouped[(date(2026, 8, 11), 10, 20, "CNY")]
    assert [row.clicks for row in shared] == [5, 7]
    assert [row.clicks for row in fallback] == [3]


@pytest.mark.asyncio
async def test_advert_product_full_snapshot_removes_stale_mapping(monkeypatch):
    db = AsyncMock()
    db.add = Mock()
    stale = SimpleNamespace(advert_id=9, nm_id=99)
    scalar_result = SimpleNamespace(all=lambda: [stale])
    db.execute.return_value = SimpleNamespace(scalars=lambda: scalar_result)
    monkeypatch.setattr(
        crud_ods_wb_advert_product,
        "_get_existing",
        AsyncMock(return_value=None),
    )

    await crud_ods_wb_advert_product.create_many(
        db,
        shop_id=1,
        adverts_data=[
            {
                "id": 10,
                "nm_settings": [
                    {
                        "nm_id": 20,
                        "bids_kopecks": {"search": 1200},
                        "subject": {"id": 3, "name": "subject"},
                    }
                ],
            }
        ],
    )

    db.delete.assert_awaited_once_with(stale)
    db.commit.assert_awaited_once()
    assert db.add.call_count == 1
