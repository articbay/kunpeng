from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.ozon.order_detail import (CRUDDWDOzonOrderDetail,
                                                _datetime, _delivery_level,
                                                _delivery_metrics,
                                                _financial_product, _hours,
                                                _money)
from kunpeng.models.dwd.ozon import DWDOzonOrderDetail
from kunpeng.models.ods.ozon.posting_reports import ODSOzonPostingReportRow


def test_ozon_order_dwd_model_uses_posting_product_grain():
    assert [column.name for column in DWDOzonOrderDetail.__table__.primary_key] == [
        "shop_id",
        "fulfillment_type",
        "posting_number",
        "sku",
    ]
    columns = DWDOzonOrderDetail.__table__.columns
    assert columns.fulfillment_type.comment == "履约方式（FBS/FBO）"
    assert "product_name_cn" in columns
    assert "delivery_city_cn" in columns
    assert "ozon_warehouse_name" in columns
    assert "seller_warehouse_name" in columns
    assert "delivery_level_1" in columns


def test_order_dwd_value_helpers_handle_real_ozon_shapes():
    assert _money({"amount": "528.50", "currency_code": "RUB"}) == (
        Decimal("528.5000"),
        "RUB",
    )
    assert (
        _financial_product(
            {"products": [{"product_id": 2098562954, "payout": 400}]},
            "2098562954",
        )["payout"]
        == 400
    )
    parsed = _datetime("2026-08-01T12:30:00Z")
    assert parsed == datetime(2026, 8, 1, 12, 30)
    assert _datetime("1970-01-01T00:00:00Z") is None
    assert _hours(datetime(2026, 8, 1), datetime(2026, 8, 2, 6)) == Decimal("30.00")


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (Decimal("0"), "01.(0,5h)"),
        (Decimal("4.99"), "01.(0,5h)"),
        (Decimal("5"), "02.(5h,12h)"),
        (Decimal("12"), "03.(12h,24h)"),
        (Decimal("24"), "04.(24h,48h)"),
        (Decimal("48"), "05.(48h,72h)"),
        (Decimal("72"), "06.(72h,96h)"),
        (Decimal("96"), "07.(96h,+)"),
        (Decimal("-0.01"), None),
        (None, None),
    ],
)
def test_delivery_level_matches_reference_workbook(hours, expected):
    assert _delivery_level(hours) == expected


def test_delivery_metrics_use_process_time_as_both_formula_baselines():
    process_at = datetime(2026, 8, 1, 0, 0)
    transferred_at = datetime(2026, 8, 2, 6, 0)
    delivery_date = datetime(2026, 8, 3, 12, 0)

    assert _delivery_metrics(process_at, transferred_at, delivery_date) == {
        "delivery_duration_1_hours": Decimal("30.00"),
        "delivery_duration_2_hours": Decimal("60.00"),
        "delivery_level_1": "04.(24h,48h)",
        "delivery_level_2": "05.(48h,72h)",
    }


@pytest.mark.asyncio
async def test_order_dwd_upsert_combines_fbs_and_fbo(monkeypatch):
    crud = CRUDDWDOzonOrderDetail()
    fbs_record = {
        "shop_id": 7,
        "fulfillment_type": "FBS",
        "posting_number": "fbs-1",
        "sku": 101,
        "order_type_name": "来自我的仓库",
    }
    fbo_record = {
        "shop_id": 7,
        "fulfillment_type": "FBO",
        "posting_number": "fbo-1",
        "sku": 202,
        "order_type_name": "来自Ozon仓库",
    }
    monkeypatch.setattr(crud, "_fbs_records", AsyncMock(return_value=[fbs_record]))
    monkeypatch.setattr(crud, "_fbo_records", AsyncMock(return_value=[fbo_record]))
    monkeypatch.setattr(
        crud,
        "_merge_report_records",
        AsyncMock(return_value=[fbs_record, fbo_record]),
    )
    db = AsyncMock()
    execute_result = Mock()
    execute_result.rowcount = 2
    db.execute.return_value = execute_result

    result = await crud.upsert_from_ods(db, shop_id=7)

    assert result == {
        "source_count": 2,
        "fbs_count": 1,
        "fbo_count": 1,
        "affected_rows": 2,
    }
    crud._fbs_records.assert_awaited_once_with(db, 7)
    crud._fbo_records.assert_awaited_once_with(db, 7)
    crud._merge_report_records.assert_awaited_once_with(db, [fbs_record, fbo_record], 7)
    db.execute.assert_awaited_once()
    upsert_sql = str(db.execute.await_args.args[0])
    assert "delivery_city_cn" in upsert_sql
    assert "CASE WHEN" in upsert_sql
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_dwd_upsert_skips_write_without_ods_rows(monkeypatch):
    crud = CRUDDWDOzonOrderDetail()
    monkeypatch.setattr(crud, "_fbs_records", AsyncMock(return_value=[]))
    monkeypatch.setattr(crud, "_fbo_records", AsyncMock(return_value=[]))
    monkeypatch.setattr(crud, "_merge_report_records", AsyncMock(return_value=[]))
    db = AsyncMock()

    result = await crud.upsert_from_ods(db)

    assert result == {
        "source_count": 0,
        "fbs_count": 0,
        "fbo_count": 0,
        "affected_rows": 0,
    }
    db.execute.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_dwd_report_values_override_list_api_values():
    crud = CRUDDWDOzonOrderDetail()
    base = {
        "shop_id": 7,
        "fulfillment_type": "FBS",
        "posting_number": "posting-1",
        "sku": 101,
        "order_type_name": "来自我的仓库",
        "seller_price": Decimal("500.0000"),
    }
    report = ODSOzonPostingReportRow(
        shop_id=7,
        task_id=1,
        report_code="report-1",
        fulfillment_type="FBS",
        posting_number="posting-1",
        sku=101,
        row_data={},
        seller_price=Decimal("499.0000"),
        delivery_fee=Decimal("120.5000"),
        cancellation_at=datetime(2026, 8, 24, 12, 0),
        product_size="XL",
    )
    db = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = [report]
    db.execute.return_value = result

    merged = await crud._merge_report_records(db, [base], shop_id=7)

    assert len(merged) == 1
    assert merged[0]["seller_price"] == Decimal("499.0000")
    assert merged[0]["delivery_fee"] == Decimal("120.5000")
    assert merged[0]["cancellation_at"] == datetime(2026, 8, 24, 12, 0)
    assert merged[0]["product_size"] == "XL"


@pytest.mark.asyncio
async def test_order_dwd_report_does_not_create_row_without_ordinary_ods():
    crud = CRUDDWDOzonOrderDetail()
    report = ODSOzonPostingReportRow(
        shop_id=7,
        task_id=1,
        report_code="report-1",
        fulfillment_type="FBS",
        posting_number="report-only",
        sku=101,
        row_data={},
        product_name="Report product",
    )
    db = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = [report]
    db.execute.return_value = result

    merged = await crud._merge_report_records(db, [], shop_id=7)

    assert merged == []
