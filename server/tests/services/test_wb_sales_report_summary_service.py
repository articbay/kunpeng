"""Tests for the DWD financial report summary service."""

import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.sales_report_summary import (
    crud_dwd_wb_sales_report_summary,
)
from kunpeng.models.dwd.wildberries.sales_report_summary import DWDWBSalesReportSummary
from kunpeng.services.wb_sales_report_summary_service import (
    wb_sales_report_summary_service,
)


def _summary() -> DWDWBSalesReportSummary:
    summary = DWDWBSalesReportSummary(
        source_ods_id=1,
        shop_id=8,
        report_id=9001,
        seller_finance_name="测试法人",
        date_from=date(2026, 7, 21),
        date_to=date(2026, 7, 27),
        create_date=date(2026, 7, 28),
        retail_amount_sum=Decimal("1000.00"),
        bank_payment_sum=Decimal("800.00"),
        currency="RUB",
    )
    summary.id = 11
    summary.create_time = datetime(2026, 7, 28, 10, 30)
    return summary


@pytest.mark.asyncio
async def test_list_summaries_returns_page(monkeypatch):
    list_summaries = AsyncMock(return_value=([_summary()], 12))
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_summary,
        "list_summaries",
        list_summaries,
    )

    result = await wb_sales_report_summary_service.list_summaries(
        Mock(),
        shop_id=8,
        page=1,
        page_size=20,
        seller_finance_name="测试",
    )

    assert result.total == 12
    assert result.items[0].report_id == 9001
    assert result.items[0].bank_payment_sum == Decimal("800.00")
    assert list_summaries.await_args.kwargs["shop_id"] == 8
    assert list_summaries.await_args.kwargs["seller_finance_name"] == "测试"


@pytest.mark.asyncio
async def test_export_summaries_builds_valid_xlsx(monkeypatch):
    list_for_export = AsyncMock(return_value=[_summary()])
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_summary,
        "list_summaries_for_export",
        list_for_export,
    )
    monkeypatch.setattr(
        "kunpeng.services.wb_sales_report_summary_service.shop_crud.get_names_by_ids",
        AsyncMock(return_value={8: "测试店铺"}),
    )

    content = await wb_sales_report_summary_service.export_summaries(
        Mock(),
        shop_id=8,
    )

    with zipfile.ZipFile(BytesIO(content)) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert 'name="财务报表周汇总"' in workbook_xml
    assert "报告编号" in sheet_xml
    assert "店铺名称" in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "应付总额" in sheet_xml
    assert "测试法人" in sheet_xml
    assert "主键ID" not in sheet_xml
    assert "来源 ods_wb_sales_report_list.id" not in sheet_xml
