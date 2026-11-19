"""Tests for the Wildberries sales report ODS-to-DWD mapping."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.finance import (
    DIRECT_ODS_FIELDS,
    DWD_BUSINESS_FIELDS,
    crud_dwd_wb_sales_report_detail,
)
from kunpeng.models.ods.wildberries.finance import ODSWBSalesReport
from kunpeng.services.wb_dwd_service import wb_dwd_service


def _source(
    *,
    source_id: int,
    shop_id: int,
    rrd_id: int,
    kiz: str | None,
) -> ODSWBSalesReport:
    source = ODSWBSalesReport(
        shop_id=shop_id,
        row_data={"kiz": kiz},
        report_id=9001,
        date_from=date(2026, 7, 21),
        date_to=date(2026, 7, 27),
        rrd_id=rrd_id,
        nm_id=123456,
        seller_oper_name="Продажа",
        retail_amount=Decimal("99.90"),
        for_pay=Decimal("75.25"),
    )
    source.id = source_id
    return source


def _mock_db(existing: list | None = None) -> Mock:
    db = Mock()
    db.execute = AsyncMock(
        return_value=Mock(
            scalars=Mock(
                return_value=Mock(all=Mock(return_value=existing or [])),
            ),
        )
    )
    db.add = Mock()
    db.flush = AsyncMock()
    return db


def test_mapping_contains_exactly_74_business_fields():
    assert len(DIRECT_ODS_FIELDS) == 73
    assert len(DWD_BUSINESS_FIELDS) == 74
    assert len(set(DWD_BUSINESS_FIELDS)) == 74
    assert DWD_BUSINESS_FIELDS[56] == "kiz"
    assert "date_to" not in DWD_BUSINESS_FIELDS
    assert "report_id" not in DWD_BUSINESS_FIELDS
    assert "row_data" not in DWD_BUSINESS_FIELDS


@pytest.mark.asyncio
async def test_upsert_maps_kiz_and_updates_existing_business_key():
    source = _source(
        source_id=7,
        shop_id=1,
        rrd_id=10001,
        kiz="mark-code",
    )
    first_db = _mock_db()

    first_stats = await crud_dwd_wb_sales_report_detail.upsert_source_batch(
        first_db,
        sources=[source],
    )
    created = first_db.add.call_args.args[0]

    assert first_stats == {"created": 1, "updated": 0}
    assert created.source_ods_id == source.id
    assert created.shop_id == source.shop_id
    assert created.rrd_id == source.rrd_id
    assert created.kiz == "mark-code"
    assert created.retail_amount == Decimal("99.90")

    updated_source = _source(
        source_id=7,
        shop_id=1,
        rrd_id=10001,
        kiz="updated-mark-code",
    )
    updated_source.for_pay = Decimal("80.00")
    second_db = _mock_db([created])

    second_stats = await crud_dwd_wb_sales_report_detail.upsert_source_batch(
        second_db,
        sources=[updated_source],
    )

    assert second_stats == {"created": 0, "updated": 1}
    second_db.add.assert_not_called()
    assert created.kiz == "updated-mark-code"
    assert created.for_pay == Decimal("80.00")


@pytest.mark.asyncio
async def test_service_filters_source_scan_by_shop(monkeypatch):
    source = _source(
        source_id=7,
        shop_id=22,
        rrd_id=10001,
        kiz=None,
    )
    get_source_batch = AsyncMock(side_effect=[[source], []])
    upsert_source_batch = AsyncMock(return_value={"created": 1, "updated": 0})
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_detail,
        "get_source_batch",
        get_source_batch,
    )
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_detail,
        "upsert_source_batch",
        upsert_source_batch,
    )
    db = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    stats = await wb_dwd_service.sync_sales_report_detail(
        db,
        shop_id=22,
        batch_size=10,
    )

    assert stats == {"scanned": 1, "created": 1, "updated": 0}
    assert get_source_batch.await_args_list[0].kwargs == {
        "after_id": 0,
        "batch_size": 10,
        "shop_id": 22,
    }
    assert get_source_batch.await_args_list[1].kwargs == {
        "after_id": 7,
        "batch_size": 10,
        "shop_id": 22,
    }
