"""Tests for the Wildberries sales report summary ODS-to-DWD mapping."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.sales_report_summary import (
    SUMMARY_FIELDS,
    crud_dwd_wb_sales_report_summary,
)
from kunpeng.models.ods.wildberries.sales_report_list import ODSWBSalesReportList
from kunpeng.services.wb_dwd_service import wb_dwd_service


def _source(
    *,
    source_id: int,
    shop_id: int,
    report_id: int,
    payment_schedule: str | None = "-1.25",
) -> ODSWBSalesReportList:
    source = ODSWBSalesReportList(
        shop_id=shop_id,
        report_id=report_id,
        seller_finance_name="山西光义科技有限公司",
        date_from=date(2026, 7, 20),
        date_to=date(2026, 7, 26),
        create_date=date(2026, 7, 27),
        currency="CNY",
        report_type=1,
        retail_amount_sum=Decimal("258.00"),
        cashback_discount_sum=Decimal("19.00"),
        for_pay_sum=Decimal("183.79"),
        avg_sale_percent=Decimal("0.0000"),
        delivery_service_sum=Decimal("25.00"),
        paid_storage_sum=Decimal("6.00"),
        paid_acceptance_sum=Decimal("2.00"),
        deduction_sum=Decimal("1.00"),
        penalty_sum=Decimal("3.00"),
        additional_payment_sum=Decimal("9.00"),
        cashback_commission_change_sum=Decimal("0.20"),
        cashback_amount_sum=Decimal("2.00"),
        payment_schedule=payment_schedule,
        bank_payment_sum=Decimal("172.34"),
        row_data={"reportId": report_id},
        synced_at=datetime(2026, 7, 27, 3, 5),
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


def test_summary_mapping_matches_21_excel_headers():
    assert len(SUMMARY_FIELDS) == 21
    assert len(set(SUMMARY_FIELDS)) == 21
    assert SUMMARY_FIELDS[0] == "report_id"
    assert SUMMARY_FIELDS[1] == "seller_finance_name"
    assert SUMMARY_FIELDS[-1] == "currency"


@pytest.mark.asyncio
async def test_upsert_converts_payment_schedule_and_updates_existing_report():
    source = _source(source_id=8, shop_id=1, report_id=307401554)
    first_db = _mock_db()

    first_stats = await crud_dwd_wb_sales_report_summary.upsert_source_batch(
        first_db,
        sources=[source],
    )
    created = first_db.add.call_args.args[0]

    assert first_stats == {"created": 1, "updated": 0}
    assert created.source_ods_id == 8
    assert created.shop_id == 1
    assert created.report_id == 307401554
    assert created.seller_finance_name == "山西光义科技有限公司"
    assert created.payment_schedule == Decimal("-1.25")
    assert created.bank_payment_sum == Decimal("172.34")

    updated_source = _source(
        source_id=8,
        shop_id=1,
        report_id=307401554,
        payment_schedule="2.50",
    )
    updated_source.bank_payment_sum = Decimal("190.00")
    second_db = _mock_db([created])

    second_stats = await crud_dwd_wb_sales_report_summary.upsert_source_batch(
        second_db,
        sources=[updated_source],
    )

    assert second_stats == {"created": 0, "updated": 1}
    second_db.add.assert_not_called()
    assert created.payment_schedule == Decimal("2.50")
    assert created.bank_payment_sum == Decimal("190.00")


def test_invalid_payment_schedule_is_cleaned_to_null():
    source = _source(
        source_id=8,
        shop_id=1,
        report_id=307401554,
        payment_schedule="unknown",
    )

    data = crud_dwd_wb_sales_report_summary.build_dwd_data(source)

    assert data["payment_schedule"] is None


@pytest.mark.asyncio
async def test_service_filters_summary_source_scan_by_shop(monkeypatch):
    source = _source(source_id=8, shop_id=22, report_id=307401554)
    get_source_batch = AsyncMock(side_effect=[[source], []])
    upsert_source_batch = AsyncMock(return_value={"created": 1, "updated": 0})
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_summary,
        "get_source_batch",
        get_source_batch,
    )
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_summary,
        "upsert_source_batch",
        upsert_source_batch,
    )
    db = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    stats = await wb_dwd_service.sync_sales_report_summary(
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
        "after_id": 8,
        "batch_size": 10,
        "shop_id": 22,
    }
