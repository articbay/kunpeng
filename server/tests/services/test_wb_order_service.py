from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.wb_order import (
    WBOrderExportRequest,
    WBOrderFilters,
    WBOrderItem,
    WBOrderKey,
)
from kunpeng.services.wb_order_service import ORDER_EXPORT_COLUMNS, WBOrderService

EXPECTED_FIELDS = [
    "shop_id",
    "order_id",
    "supply_id",
    "sticker_id",
    "order_dt",
    "title",
    "title_cn",
    "tech_size",
    "tech_size_cn",
    "color",
    "color_cn",
    "barcode_ori",
    "barcode_hand",
    "retail_price",
    "currency",
    "nm_id",
    "supplier_article",
    "warehouse_id",
    "warehouse_name",
    "warehouse_name_cn",
    "wb_status",
    "wb_status_cn",
    "address",
    "address_cn",
    "is_b2b",
    "delivery_type",
    "supplier_status",
    "supplier_status_cn",
    "is_cancellable",
    "price",
    "converted_price",
    "currency_code",
    "converted_currency_code",
    "order_price",
    "currency_name",
    "office_id",
    "cargo_type",
    "cross_border_type",
    "is_zero_order",
]


def _record(**overrides):
    values = {
        "shop_id": 8,
        "order_id": 123456,
        "supply_id": "supply-1",
        "sticker_id": "sticker-1",
        "order_dt": datetime(2026, 7, 21, 8, 36, 17),
        "title": "title",
        "title_cn": "商品名称",
        "tech_size": "M",
        "tech_size_cn": "中码",
        "color": "blue",
        "color_cn": "蓝色",
        "barcode_ori": "2044420598851",
        "barcode_hand": "TG-HC02904",
        "retail_price": Decimal("129.90"),
        "currency": "cny",
        "nm_id": 1214137012,
        "supplier_article": "article-1",
        "warehouse_id": 77,
        "warehouse_name": "warehouse",
        "warehouse_name_cn": "仓库",
        "wb_status": "waiting",
        "wb_status_cn": "等待中",
        "address": "address",
        "address_cn": "地址",
        "is_b2b": False,
        "delivery_type": "fbs",
        "supplier_status": "confirm",
        "supplier_status_cn": "已确认",
        "is_cancellable": True,
        "price": Decimal("130.00"),
        "converted_price": Decimal("12990.00"),
        "currency_code": 643,
        "converted_currency_code": 156,
        "office_id": 88,
        "cargo_type": 1,
        "cross_border_type": 0,
        "is_zero_order": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_order_response_has_dwd_and_normalized_display_fields():
    assert list(WBOrderItem.model_fields) == EXPECTED_FIELDS


@pytest.mark.asyncio
async def test_list_orders_uses_moscow_date_bounds_and_serializes_time():
    service = WBOrderService()
    filters = WBOrderFilters(
        date_from=date(2026, 7, 20),
        date_to=date(2026, 7, 21),
        wb_status="waiting",
        supplier_status="confirm",
        delivery_type="fbs",
        is_cancellable=True,
        is_b2b=False,
        is_zero_order=False,
    )

    with (
        patch(
            "kunpeng.services.wb_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_order_service." "crud_dwd_wb_order_detail.list_orders",
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
    assert response.items[0].order_dt.isoformat() == ("2026-07-21T11:36:17+03:00")
    assert response.items[0].wb_status_cn == "待WB接收"
    assert response.items[0].supplier_status_cn == "组装中"
    assert response.items[0].order_price == Decimal("129.90")
    assert response.items[0].currency_name == "人民币"
    kwargs = list_orders.await_args.kwargs
    assert kwargs["order_from"] == datetime(2026, 7, 19, 21, 0)
    assert kwargs["order_to"] == datetime(2026, 7, 21, 21, 0)
    assert kwargs["wb_status"] == "waiting"
    assert kwargs["supplier_status"] == "confirm"
    assert kwargs["delivery_type"] == "fbs"
    assert kwargs["is_cancellable"] is True
    assert kwargs["is_b2b"] is False
    assert kwargs["is_zero_order"] is False


@pytest.mark.asyncio
async def test_selected_order_export_builds_xlsx_with_moscow_time():
    service = WBOrderService()
    export_request = WBOrderExportRequest(
        scope="selected",
        selected_keys=[WBOrderKey(shop_id=8, order_id=123456)],
    )

    with (
        patch(
            "kunpeng.services.wb_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_order_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={8: "测试店铺"}),
        ),
        patch(
            "kunpeng.services.wb_order_service."
            "crud_dwd_wb_order_detail.list_orders_by_keys",
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
    assert "人民币" in sheet_xml
    assert "订单价格" in sheet_xml
    assert "折算价格" not in sheet_xml
    assert "货币代码" not in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "待WB接收" in sheet_xml
    assert "组装中" in sheet_xml
    assert "WB履约订单" in workbook_xml


def test_unknown_converted_currency_preserves_the_code_for_display():
    item = WBOrderService._build_item(
        _record(converted_currency_code=999, converted_price=Decimal("12345"))
    )

    assert item.order_price == Decimal("123.45")
    assert item.currency_name == "999"


def test_export_columns_keep_all_populated_dwd_values():
    item = WBOrderService._build_item(_record())
    row = item.model_dump(mode="python")

    for label, field in ORDER_EXPORT_COLUMNS:
        if field == "shop_name":
            continue
        assert field in row, f"导出字段未在接口模型中定义：{label} ({field})"
        assert row[field] is not None, f"导出字段丢失已有值：{label} ({field})"


@pytest.mark.parametrize(
    ("status", "stored_translation", "expected"),
    [
        ("sorted", None, "WB已接收并分拣"),
        (" SORTED ", "错误译文", "WB已接收并分拣"),
        ("waiting", "等待中", "待WB接收"),
        ("unknown", "已有译文", "已有译文"),
    ],
)
def test_order_status_uses_reviewed_dictionary_and_preserves_unknowns(
    status, stored_translation, expected
):
    item = WBOrderService._build_item(
        _record(wb_status=status, wb_status_cn=stored_translation)
    )

    assert item.wb_status_cn == expected


@pytest.mark.parametrize(
    ("status", "stored_translation", "expected"),
    [
        ("new", None, "新订单"),
        ("confirm", "已确认", "组装中"),
        ("deliver", "投递", "配送中"),
        ("unknown", "已有译文", "已有译文"),
    ],
)
def test_supplier_status_uses_lifecycle_dictionary_and_preserves_unknowns(
    status, stored_translation, expected
):
    item = WBOrderService._build_item(
        _record(
            supplier_status=status,
            supplier_status_cn=stored_translation,
        )
    )

    assert item.supplier_status_cn == expected
