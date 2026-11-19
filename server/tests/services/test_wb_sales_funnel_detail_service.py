"""Tests for the DWD sales funnel detail service."""

import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.funnel import crud_dwd_wb_sales_funnel_detail
from kunpeng.models.dwd.wildberries.funnel import DWDWBSalesFunnelDetail
from kunpeng.services.wb_sales_funnel_detail_service import (
    wb_sales_funnel_detail_service,
)


def _detail() -> DWDWBSalesFunnelDetail:
    detail = DWDWBSalesFunnelDetail(
        source_ods_id=1,
        shop_id=8,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 7),
        nm_id=123456,
        vendor_code="ABC-001",
        title="测试商品",
        open_count=120,
        order_sum=Decimal("1000.00"),
    )
    detail.id = 11
    detail.create_time = datetime(2026, 7, 8, 10, 30)
    return detail


@pytest.mark.asyncio
async def test_list_details_returns_page(monkeypatch):
    list_details = AsyncMock(return_value=([_detail()], 25))
    monkeypatch.setattr(
        crud_dwd_wb_sales_funnel_detail,
        "list_details",
        list_details,
    )

    result = await wb_sales_funnel_detail_service.list_details(
        Mock(),
        shop_id=8,
        page=2,
        page_size=10,
        vendor_code="ABC",
    )

    assert result.total == 25
    assert result.page == 2
    assert result.page_size == 10
    assert result.items[0].nm_id == 123456
    assert result.items[0].title == "测试商品"
    assert list_details.await_args.kwargs["shop_id"] == 8
    assert list_details.await_args.kwargs["vendor_code"] == "ABC"


@pytest.mark.asyncio
async def test_export_details_builds_valid_xlsx(monkeypatch):
    list_for_export = AsyncMock(return_value=[_detail()])
    monkeypatch.setattr(
        crud_dwd_wb_sales_funnel_detail,
        "list_details_for_export",
        list_for_export,
    )
    monkeypatch.setattr(
        "kunpeng.services.wb_sales_funnel_detail_service.shop_crud.get_names_by_ids",
        AsyncMock(return_value={8: "测试店铺"}),
    )

    content = await wb_sales_funnel_detail_service.export_details(
        Mock(),
        shop_id=8,
    )

    with zipfile.ZipFile(BytesIO(content)) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert 'name="销售漏斗明细"' in workbook_xml
    assert "主键ID" not in sheet_xml
    assert "店铺ID" in sheet_xml
    assert "店铺名称" in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "统计结束日期" in sheet_xml
    assert "统计结束日期（技术字段）" not in sheet_xml
    assert "卖家商品编号" in sheet_xml
    assert "创建时间" in sheet_xml
    assert "来源 ods_wb_sales_funnels.id" not in sheet_xml
    assert "ABC-001" in sheet_xml
    assert "测试商品" in sheet_xml
