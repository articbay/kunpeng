from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.wb_order_statistics import (
    WBOrderStatisticsExportRequest,
    WBOrderStatisticsFilters,
    WBOrderStatisticsItem,
    WBOrderStatisticsKey,
)
from kunpeng.services.wb_order_statistics_service import WBOrderStatisticsService

EXPECTED_FIELDS = [
    "shop_id",
    "srid",
    "order_date",
    "last_change_date",
    "warehouse_name",
    "warehouse_name_cn",
    "country_name",
    "country_name_cn",
    "oblast_okrug_name",
    "oblast_okrug_name_cn",
    "region_name",
    "region_name_cn",
    "supplier_article",
    "nm_id",
    "barcode_ori",
    "barcode_hand",
    "category",
    "category_cn",
    "subject_name",
    "subject_name_cn",
    "tech_size",
    "tech_size_cn",
    "total_price",
    "discount_percent",
    "price_with_disc",
    "finished_price",
    "is_cancel",
    "cancel_date",
    "sticker_id",
    "g_number",
]


def _record(**overrides):
    values = {
        "shop_id": 8,
        "srid": "srid-1",
        "order_date": datetime(2026, 7, 21, 11, 36, 17),
        "last_change_date": datetime(2026, 7, 21, 12, 0, 0),
        "warehouse_name": "warehouse",
        "warehouse_name_cn": "仓库",
        "country_name": "country",
        "country_name_cn": "国家",
        "oblast_okrug_name": "okrug",
        "oblast_okrug_name_cn": "联邦管区",
        "region_name": "region",
        "region_name_cn": "地区",
        "supplier_article": "article-1",
        "nm_id": 1214137012,
        "barcode_ori": "2044420598851",
        "barcode_hand": "TG-HC02904",
        "category": "category",
        "category_cn": "商品分类",
        "subject_name": "subject",
        "subject_name_cn": "商品品类",
        "tech_size": "M",
        "tech_size_cn": "中码",
        "total_price": Decimal("150.00"),
        "discount_percent": 10,
        "price_with_disc": Decimal("135.00"),
        "finished_price": Decimal("129.90"),
        "is_cancel": False,
        "cancel_date": None,
        "sticker_id": "sticker-1",
        "g_number": "group-1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_statistics_order_response_has_only_dwd_fields():
    assert list(WBOrderStatisticsItem.model_fields) == EXPECTED_FIELDS


@pytest.mark.asyncio
async def test_list_statistics_orders_keeps_moscow_local_time_and_bounds():
    service = WBOrderStatisticsService()
    filters = WBOrderStatisticsFilters(
        date_from=date(2026, 7, 20),
        date_to=date(2026, 7, 21),
        is_cancel=False,
    )

    with (
        patch(
            "kunpeng.services.wb_order_statistics_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_order_statistics_service."
            "crud_dwd_wb_order_statistics_detail.list_orders",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_orders,
    ):
        response = await service.list_orders(
            AsyncMock(),
            user_id=3,
            filters=filters,
            page=1,
            page_size=20,
        )

    assert response.total == 1
    assert response.items[0].order_date.isoformat() == ("2026-07-21T11:36:17+03:00")
    kwargs = list_orders.await_args.kwargs
    assert kwargs["order_from"] == datetime(2026, 7, 20, 0, 0)
    assert kwargs["order_to"] == datetime(2026, 7, 22, 0, 0)
    assert kwargs["is_cancel"] is False


@pytest.mark.asyncio
async def test_selected_statistics_order_export_builds_xlsx():
    service = WBOrderStatisticsService()
    export_request = WBOrderStatisticsExportRequest(
        scope="selected",
        selected_keys=[WBOrderStatisticsKey(shop_id=8, srid="srid-1")],
    )

    with (
        patch(
            "kunpeng.services.wb_order_statistics_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_order_statistics_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={8: "测试店铺"}),
        ),
        patch(
            "kunpeng.services.wb_order_statistics_service."
            "crud_dwd_wb_order_statistics_detail.list_orders_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
    ):
        content = await service.export_orders(
            AsyncMock(),
            user_id=3,
            export_request=export_request,
        )

    assert content.startswith(b"PK")
    assert list_by_keys.await_args.kwargs["allowed_shop_ids"] == [8]
    with ZipFile(BytesIO(content)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
    assert "2026-07-21 11:36:17" in sheet_xml
    assert "129.90" in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "WB统计订单" in workbook_xml
