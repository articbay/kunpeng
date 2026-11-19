"""Wildberries 财务报表列表幂等写入测试。"""

from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.ods.wildberries.sales_report_list import \
    crud_ods_wb_sales_report_list


@pytest.mark.asyncio
async def test_upsert_many_updates_same_shop_and_report():
    db = AsyncMock()
    db.add = Mock()
    first_lookup = Mock()
    first_lookup.scalar_one_or_none.return_value = None
    second_lookup = Mock()
    second_lookup.scalar_one_or_none.side_effect = lambda: created_record
    db.execute.side_effect = [first_lookup, second_lookup]

    report = {
        "reportId": 922337203685000000,
        "sellerFinanceName": "Test Seller",
        "dateFrom": "2026-07-20",
        "dateTo": "2026-07-26",
        "createDate": "2026-07-27",
        "currency": "RUB",
        "reportType": 1,
        "retailAmountSum": "258",
        "forPaySum": "183.79",
        "bankPaymentSum": "150",
    }
    await crud_ods_wb_sales_report_list.upsert_many(
        db,
        shop_id=1,
        reports=[report],
    )
    created_record = db.add.call_args.args[0]

    updated_report = {**report, "forPaySum": "200.25"}
    await crud_ods_wb_sales_report_list.upsert_many(
        db,
        shop_id=1,
        reports=[updated_report],
    )

    assert db.add.call_count == 1
    assert db.commit.await_count == 2
    assert created_record.report_id == 922337203685000000
    assert float(created_record.for_pay_sum) == 200.25
    assert created_record.row_data["forPaySum"] == "200.25"
