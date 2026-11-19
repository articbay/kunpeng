"""Tests for the Wildberries financial report detail service."""

import zipfile
from datetime import date
from io import BytesIO
from unittest.mock import AsyncMock, Mock
from xml.etree import ElementTree

import pytest

from kunpeng.crud.dwd.wildberries.finance import crud_dwd_wb_sales_report_detail
from kunpeng.models.dwd.wildberries.finance import DWDWBSalesReportDetail
from kunpeng.services.wb_financial_report_service import wb_financial_report_service


def _detail() -> DWDWBSalesReportDetail:
    detail = DWDWBSalesReportDetail(
        source_ods_id=1,
        shop_id=8,
        date_from=date(2026, 7, 20),
        rrd_id=10001,
        vendor_code="ABC-001",
    )
    detail.id = 11
    return detail


@pytest.mark.asyncio
async def test_list_report_details_returns_page(monkeypatch):
    list_details = AsyncMock(return_value=([_detail()], 25))
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_detail,
        "list_report_details",
        list_details,
    )

    result = await wb_financial_report_service.list_report_details(
        Mock(),
        shop_id=8,
        page=2,
        page_size=10,
        vendor_code="ABC",
    )

    assert result.total == 25
    assert result.page == 2
    assert result.page_size == 10
    assert result.items[0].rrd_id == 10001
    assert result.items[0].vendor_code == "ABC-001"
    assert list_details.await_args.kwargs["shop_id"] == 8
    assert list_details.await_args.kwargs["vendor_code"] == "ABC"


@pytest.mark.asyncio
async def test_export_report_details_builds_valid_xlsx(monkeypatch):
    list_for_export = AsyncMock(return_value=[_detail()])
    monkeypatch.setattr(
        crud_dwd_wb_sales_report_detail,
        "list_report_details_for_export",
        list_for_export,
    )
    monkeypatch.setattr(
        "kunpeng.services.wb_financial_report_service.shop_crud.get_names_by_ids",
        AsyncMock(return_value={8: "测试店铺"}),
    )

    content = await wb_financial_report_service.export_report_details(
        Mock(),
        shop_id=8,
    )

    with zipfile.ZipFile(BytesIO(content)) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

        for member in workbook.namelist():
            if member.endswith((".xml", ".rels")):
                ElementTree.fromstring(workbook.read(member))

    assert 'name="财务报告周明细"' in workbook_xml
    workbook_root = ElementTree.fromstring(workbook_xml)
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    assert len(workbook_root.findall("main:sheets", namespace)) == 1
    assert len(workbook_root.findall("main:sheets/main:sheet", namespace)) == 1
    assert "财务报告周开始日期" in sheet_xml
    assert "店铺名称" in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "ABC-001" in sheet_xml
