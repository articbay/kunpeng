"""Tests for DWD sales funnel detail query CRUD."""

from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.funnel import crud_dwd_wb_sales_funnel_detail


@pytest.mark.asyncio
async def test_list_details_applies_filters_and_pagination():
    count_result = Mock()
    count_result.scalar_one.return_value = 31
    row = Mock()
    rows_result = Mock()
    rows_result.scalars.return_value.all.return_value = [row]
    db = Mock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    records, total = await crud_dwd_wb_sales_funnel_detail.list_details(
        db,
        shop_id=8,
        page=2,
        page_size=10,
        vendor_code="ABC",
        title="商品",
        subject_name="品类",
        brand_name="品牌",
    )

    assert records == [row]
    assert total == 31
    assert db.execute.await_count == 2
    list_statement = db.execute.await_args_list[1].args[0]
    params = list_statement.compile().params
    assert params["param_1"] == 10
    assert params["param_2"] == 10
    statement_text = str(list_statement)
    assert "shop_id" in statement_text
    assert "vendor_code" in statement_text
    assert "title" in statement_text
    assert "subject_name" in statement_text
    assert "brand_name" in statement_text
