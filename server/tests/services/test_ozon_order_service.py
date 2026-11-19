from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.ozon_order import (OzonOrderExportRequest,
                                        OzonOrderFilters, OzonOrderKey)
from kunpeng.services.ozon_order_service import (FILTERED_EXPORT_LIMIT,
                                                 ExportLimitExceededError,
                                                 OzonOrderService)


def _record(**overrides):
    values = {
        "shop_id": 2,
        "fulfillment_type": "FBS",
        "posting_number": "12345-0001-1",
        "sku": 987654321,
        "order_type_name": "来自我的仓库",
        "order_id": 12345,
        "order_number": "12345-0001",
        "in_process_month": date(2026, 7, 1),
        "in_process_date": date(2026, 7, 20),
        "in_process_at": datetime(2026, 7, 20, 12, 30),
        "delivery_duration_1_hours": Decimal("30.00"),
        "delivery_duration_2_hours": Decimal("60.00"),
        "delivery_level_1": "04.(24h,48h)",
        "delivery_level_2": "05.(48h,72h)",
        "status_code": "delivered",
        "status_name_cn": "已送达",
        "product_name": "Travel bag",
        "product_name_cn": "旅行包",
        "delivery_city": "Москва",
        "delivery_city_cn": "莫斯科",
        "seller_price": Decimal("999.50"),
        "buyer_paid_amount": Decimal("949.50"),
        "promotion_actions": [{"title": "Summer sale"}],
        "buyer_name": "Raw Buyer Name",
        "buyer_phone": "+70000000000",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_list_orders_enforces_ozon_shop_scope_and_filters():
    service = OzonOrderService()
    filters = OzonOrderFilters(
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        fulfillment_type="FBS",
        sku=987654321,
        delivery_city="Moscow",
    )

    with (
        patch(
            "kunpeng.services.ozon_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[2, 5]),
        ) as allowed_shops,
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.list_orders",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_orders,
    ):
        response = await service.list_orders(
            AsyncMock(), user_id=7, filters=filters, page=1, page_size=20
        )

    assert response.total == 1
    assert response.items[0].product_name_cn == "旅行包"
    assert response.items[0].delivery_city_cn == "莫斯科"
    assert allowed_shops.await_args.kwargs == {"user_id": 7, "platform": "ozon"}
    kwargs = list_orders.await_args.kwargs
    assert kwargs["allowed_shop_ids"] == [2, 5]
    assert kwargs["date_from"] == date(2026, 7, 1)
    assert kwargs["date_to"] == date(2026, 7, 31)
    assert kwargs["fulfillment_type"] == "FBS"
    assert kwargs["sku"] == 987654321
    assert kwargs["delivery_city"] == "Moscow"


@pytest.mark.asyncio
async def test_selected_export_uses_four_column_key_and_keeps_raw_buyer_data():
    service = OzonOrderService()
    key = OzonOrderKey(
        shop_id=2,
        fulfillment_type="FBS",
        posting_number="12345-0001-1",
        sku=987654321,
    )
    request = OzonOrderExportRequest(scope="selected", selected_keys=[key])

    with (
        patch(
            "kunpeng.services.ozon_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[2]),
        ),
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.list_orders_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
        patch(
            "kunpeng.services.ozon_order_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={2: "莫斯科一店"}),
        ) as get_shop_names,
    ):
        content = await service.export_orders(
            AsyncMock(), user_id=7, export_request=request
        )

    assert content.startswith(b"PK")
    assert list_by_keys.await_args.kwargs["keys"] == [key]
    assert get_shop_names.await_args.kwargs == {"shop_ids": [2]}
    with ZipFile(BytesIO(content)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
    assert "Raw Buyer Name" in sheet_xml
    assert "+70000000000" in sheet_xml
    assert "Summer sale" in sheet_xml
    assert "店铺名称" in sheet_xml
    assert "莫斯科一店" in sheet_xml
    assert "配送城市（中文）" in sheet_xml
    assert "莫斯科" in sheet_xml
    assert "2026年07月" in sheet_xml
    assert "04.(24h,48h)" in sheet_xml
    assert "05.(48h,72h)" in sheet_xml
    assert "Ozon统一订单" in workbook_xml


@pytest.mark.asyncio
async def test_order_export_displays_missing_delivery_metrics_as_none_text():
    service = OzonOrderService()
    key = OzonOrderKey(
        shop_id=2,
        fulfillment_type="FBS",
        posting_number="12345-0001-1",
        sku=987654321,
    )
    request = OzonOrderExportRequest(scope="selected", selected_keys=[key])
    record = _record(
        delivery_duration_1_hours=None,
        delivery_duration_2_hours=None,
        delivery_level_1=None,
        delivery_level_2=None,
    )

    with (
        patch(
            "kunpeng.services.ozon_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[2]),
        ),
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.list_orders_by_keys",
            new=AsyncMock(return_value=[record]),
        ),
        patch(
            "kunpeng.services.ozon_order_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={2: "莫斯科一店"}),
        ),
    ):
        content = await service.export_orders(
            AsyncMock(), user_id=7, export_request=request
        )

    with ZipFile(BytesIO(content)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert sheet_xml.count(">无<") == 4


@pytest.mark.asyncio
async def test_order_export_derives_missing_level_from_existing_duration():
    service = OzonOrderService()
    key = OzonOrderKey(
        shop_id=2,
        fulfillment_type="FBS",
        posting_number="12345-0001-1",
        sku=987654321,
    )
    request = OzonOrderExportRequest(scope="selected", selected_keys=[key])
    record = _record(
        delivery_duration_1_hours=Decimal("30.00"),
        delivery_level_1=None,
    )

    with (
        patch(
            "kunpeng.services.ozon_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[2]),
        ),
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.list_orders_by_keys",
            new=AsyncMock(return_value=[record]),
        ),
        patch(
            "kunpeng.services.ozon_order_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={2: "莫斯科一店"}),
        ),
    ):
        content = await service.export_orders(
            AsyncMock(), user_id=7, export_request=request
        )

    with ZipFile(BytesIO(content)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "04.(24h,48h)" in sheet_xml


@pytest.mark.asyncio
async def test_filtered_export_rejects_more_than_limit():
    service = OzonOrderService()
    request = OzonOrderExportRequest(scope="filtered")

    with (
        patch(
            "kunpeng.services.ozon_order_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[2]),
        ),
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.count_orders",
            new=AsyncMock(return_value=FILTERED_EXPORT_LIMIT + 1),
        ),
        patch(
            "kunpeng.services.ozon_order_service."
            "crud_dwd_ozon_order_query.list_orders_for_export",
            new=AsyncMock(),
        ) as export_rows,
    ):
        with pytest.raises(ExportLimitExceededError):
            await service.export_orders(AsyncMock(), user_id=7, export_request=request)

    export_rows.assert_not_awaited()
