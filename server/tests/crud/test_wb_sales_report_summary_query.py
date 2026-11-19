"""Tests for DWD financial report summary query CRUD."""

from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.sales_report_summary import (
    crud_dwd_wb_sales_report_summary,
)


@pytest.mark.asyncio
async def test_list_summaries_applies_filters_and_pagination():
    count_result = Mock()
    count_result.scalar_one.return_value = 23
    row = Mock()
    rows_result = Mock()
    rows_result.scalars.return_value.all.return_value = [row]
    db = Mock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    records, total = await crud_dwd_wb_sales_report_summary.list_summaries(
        db,
        shop_id=8,
        page=2,
        page_size=10,
        seller_finance_name="法人",
        report_type=1,
        currency="RUB",
    )

    assert records == [row]
    assert total == 23
    assert db.execute.await_count == 2
    list_statement = db.execute.await_args_list[1].args[0]
    params = list_statement.compile().params
    assert params["param_1"] == 10
    assert params["param_2"] == 10
    statement_text = str(list_statement)
    assert "shop_id" in statement_text
    assert "seller_finance_name" in statement_text
    assert "report_type" in statement_text
    assert "currency" in statement_text
