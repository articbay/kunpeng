"""Tests for DWD financial report detail query CRUD."""

from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.finance import crud_dwd_wb_sales_report_detail


@pytest.mark.asyncio
async def test_list_report_details_applies_pagination_and_filters():
    count_result = Mock()
    count_result.scalar_one.return_value = 21
    row = Mock()
    rows_result = Mock()
    rows_result.scalars.return_value.all.return_value = [row]
    db = Mock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    records, total = await crud_dwd_wb_sales_report_detail.list_report_details(
        db,
        shop_id=8,
        page=2,
        page_size=10,
        vendor_code="ABC",
        brand_name="Brand",
    )

    assert records == [row]
    assert total == 21
    assert db.execute.await_count == 2
    list_statement = db.execute.await_args_list[1].args[0]
    params = list_statement.compile().params
    assert params["param_1"] == 10
    assert params["param_2"] == 10
    assert "shop_id" in str(list_statement)
    assert "vendor_code" in str(list_statement)
    assert "brand_name" in str(list_statement)
