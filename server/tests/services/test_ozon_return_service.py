from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.ozon_return import (OzonReturnExportRequest,
                                         OzonReturnFilters, OzonReturnItem,
                                         OzonReturnKey)
from kunpeng.services.ozon_return_service import (OZON_RETURN_EXPORT_COLUMNS,
                                                  OzonReturnService)
from kunpeng.services.ozon_return_status_translation import (
    OZON_RETURN_STATUS_CN_BY_DISPLAY_NAME, resolve_ozon_return_status_cn)

EXPECTED_FIELDS = [
    "shop_id",
    "return_id",
    "nm_id",
    "schema",
    "product_name",
    "product_name_cn",
    "posting_number",
    "offer_id",
    "order_date",
    "return_date",
    "status_id",
    "status_display_name",
    "status_display_name_cn",
    "status_sys_name",
    "status_change_at",
    "compensation_status_id",
    "compensation_status_display_name",
    "compensation_status_display_name_cn",
    "compensation_status_sys_name",
    "compensation_status_change_at",
    "return_reason_name",
    "return_reason_name_cn",
    "buyer_comment",
    "buyer_comment_cn",
    "quantity",
    "is_opened",
    "target_place_name",
    "target_place_name_cn",
    "target_place_address",
    "target_place_address_cn",
    "ready_to_pickup_at",
    "place_name",
    "place_name_cn",
    "picked_up_at",
    "storage_days",
    "storage_expire_at",
    "logistic_barcode",
    "storage_fee_amount",
    "storage_fee_currency",
    "utilization_fee_amount",
    "utilization_fee_currency",
    "price_amount",
    "price_currency",
    "commission_percent",
    "commission_amount",
    "commission_currency",
    "price_without_commission_amount",
    "price_without_commission_currency",
    "brand_name",
    "category_name",
    "category_name_cn",
    "product_barcode",
    "exemplar_id",
    "utilization_forecast_at",
    "pickup_duration_hours",
    "order_id",
    "order_number",
    "srid",
    "place_id",
    "place_address",
    "place_address_cn",
    "target_place_id",
    "return_type",
    "is_super_econom",
]


def _record(**overrides):
    values = {
        "shop_id": 9,
        "return_id": 1001,
        "nm_id": 2002,
        "schema": "Fbo",
        "brand_name": "brand",
        "category_name": "Поводки",
        "category_name_cn": "牵引绳",
        "product_name": "Поводок",
        "product_name_cn": "牵引绳",
        "product_barcode": "product-barcode",
        "offer_id": "offer-1",
        "logistic_barcode": "logistic-barcode",
        "exemplar_id": 3003,
        "status_id": 4,
        "status_display_name": "Готов к выдаче",
        "status_display_name_cn": "准备引渡",
        "status_sys_name": "ready_for_pickup",
        "status_change_at": datetime(2026, 8, 1, 8, 0, 0),
        "compensation_status_id": 2,
        "compensation_status_display_name": "Компенсация получена",
        "compensation_status_display_name_cn": "已收到赔偿",
        "compensation_status_sys_name": "Received",
        "compensation_status_change_at": datetime(2026, 8, 1, 8, 30, 0),
        "buyer_comment": "Не подошёл размер",
        "buyer_comment_cn": "尺码不合适",
        "ready_to_pickup_at": datetime(2026, 8, 1, 9, 0, 0),
        "picked_up_at": datetime(2026, 8, 1, 10, 0, 0),
        "storage_expire_at": datetime(2026, 8, 5, 9, 0, 0),
        "utilization_forecast_at": None,
        "storage_days": 4,
        "pickup_duration_hours": Decimal("1.00"),
        "order_date": datetime(2026, 7, 31, 21, 30, 0),
        "return_reason_name": "Причина",
        "return_reason_name_cn": "原因",
        "posting_number": "posting-1",
        "order_id": 4004,
        "order_number": "order-1",
        "srid": "order-1",
        "place_id": 5005,
        "place_name": "Склад",
        "place_name_cn": "仓库",
        "place_address": "Москва",
        "place_address_cn": "莫斯科",
        "target_place_id": 6006,
        "target_place_name": "Пункт выдачи",
        "target_place_name_cn": "提货点",
        "target_place_address": "Москва, улица",
        "target_place_address_cn": "莫斯科，街道",
        "return_type": "ClientReturn",
        "return_date": datetime(2026, 8, 1, 11, 0, 0),
        "is_opened": True,
        "is_super_econom": False,
        "quantity": 1,
        "price_amount": Decimal("99.5000"),
        "price_currency": "RUB",
        "storage_fee_amount": Decimal("12.5000"),
        "storage_fee_currency": "RUB",
        "utilization_fee_amount": Decimal("30.0000"),
        "utilization_fee_currency": "RUB",
        "commission_percent": Decimal("15.00"),
        "commission_amount": Decimal("14.9250"),
        "commission_currency": "RUB",
        "price_without_commission_amount": Decimal("84.5750"),
        "price_without_commission_currency": "RUB",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_ozon_return_response_has_only_dwd_fields():
    assert list(OzonReturnItem.model_fields) == EXPECTED_FIELDS


def test_ozon_return_export_headers_follow_reference_excel_order():
    assert [label for label, _ in OZON_RETURN_EXPORT_COLUMNS] == [
        "店铺ID",
        "店铺名称",
        "模式",
        "商品名称",
        "商品名称（中文）",
        "货件编号",
        "订单ID",
        "订单编号",
        "货号",
        "OZON SKU ID",
        "下订单日期",
        "退货日期",
        "退货状态",
        "退货状态（中文）",
        "状态日期",
        "赔偿状态",
        "赔偿状态（中文）",
        "赔偿状态日期",
        "退货原因",
        "退货原因（中文）",
        "买家评论",
        "买家评论（中文）",
        "退货数量",
        "货件已打开",
        "目的地",
        "目的地（中文）",
        "存储地址",
        "存储地址（中文）",
        "转到“到达取货点”",
        "位置",
        "位置（中文）",
        "向卖家退货日期",
        "存储天数",
        "免费存储的最后一天",
        "退货条形码",
        "仓储费用",
        "仓储费用币种",
        "销毁费用",
        "销毁费用币种",
        "商品价格",
        "商品价格币种",
        "佣金百分比",
        "佣金",
        "佣金币种",
        "不含佣金的价格",
        "不含佣金价格币种",
    ]


@pytest.mark.parametrize(
    ("status_display_name", "expected_translation"),
    OZON_RETURN_STATUS_CN_BY_DISPLAY_NAME.items(),
)
def test_reviewed_ozon_return_status_translations(
    status_display_name, expected_translation
):
    assert (
        resolve_ozon_return_status_cn(
            status_sys_name=None,
            status_display_name=status_display_name,
            stored_translation="错误的机器译文",
        )
        == expected_translation
    )


def test_unknown_ozon_return_status_keeps_stored_translation():
    assert (
        resolve_ozon_return_status_cn(
            status_sys_name="FutureStatus",
            status_display_name="Новый статус",
            stored_translation="已有译文",
        )
        == "已有译文"
    )


@pytest.mark.asyncio
async def test_list_returns_authorizes_ozon_and_uses_moscow_date_bounds():
    service = OzonReturnService()
    filters = OzonReturnFilters(
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 1),
        order_id=4004,
        status="ready",
    )

    with (
        patch(
            "kunpeng.services.ozon_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[9]),
        ) as get_shop_ids,
        patch(
            "kunpeng.services.ozon_return_service."
            "crud_dwd_ozon_return_detail.list_returns",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_returns,
    ):
        response = await service.list_returns(
            AsyncMock(), user_id=3, filters=filters, page=1, page_size=20
        )

    get_shop_ids.assert_awaited_once()
    assert get_shop_ids.await_args.kwargs == {"user_id": 3, "platform": "ozon"}
    assert response.total == 1
    assert response.items[0].order_date.isoformat() == "2026-08-01T00:30:00+03:00"
    kwargs = list_returns.await_args.kwargs
    assert kwargs["allowed_shop_ids"] == [9]
    assert kwargs["order_from"] == datetime(2026, 7, 31, 21, 0, 0)
    assert kwargs["order_to"] == datetime(2026, 8, 1, 21, 0, 0)
    assert kwargs["order_id"] == 4004
    assert kwargs["status"] == "ready"


@pytest.mark.asyncio
async def test_list_returns_overrides_machine_translation_with_reviewed_status():
    service = OzonReturnService()
    record = _record(
        status_display_name="Едет к вам",
        status_display_name_cn="他来找你",
        status_sys_name="MovingToSeller",
    )

    with (
        patch(
            "kunpeng.services.ozon_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[9]),
        ),
        patch(
            "kunpeng.services.ozon_return_service."
            "crud_dwd_ozon_return_detail.list_returns",
            new=AsyncMock(return_value=([record], 1)),
        ),
    ):
        response = await service.list_returns(
            AsyncMock(),
            user_id=3,
            filters=OzonReturnFilters(),
            page=1,
            page_size=20,
        )

    assert response.items[0].status_display_name_cn == "运输中，发往卖家"


@pytest.mark.asyncio
async def test_selected_ozon_return_export_builds_xlsx_with_moscow_times():
    service = OzonReturnService()
    export_request = OzonReturnExportRequest(
        scope="selected",
        selected_keys=[OzonReturnKey(shop_id=9, return_id=1001, nm_id=2002)],
    )

    with (
        patch(
            "kunpeng.services.ozon_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[9]),
        ),
        patch(
            "kunpeng.services.ozon_return_service."
            "crud_dwd_ozon_return_detail.list_returns_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
        patch(
            "kunpeng.services.ozon_return_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={9: "圣彼得堡店"}),
        ) as get_shop_names,
    ):
        content = await service.export_returns(
            AsyncMock(), user_id=3, export_request=export_request
        )

    assert content.startswith(b"PK")
    assert list_by_keys.await_args.kwargs["allowed_shop_ids"] == [9]
    assert get_shop_names.await_args.kwargs == {"shop_ids": [9]}
    with ZipFile(BytesIO(content)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
    assert "订单ID" in sheet_xml
    assert "4004" in sheet_xml
    assert "订单编号" in sheet_xml
    assert "order-1" in sheet_xml
    assert "店铺名称" in sheet_xml
    assert "圣彼得堡店" in sheet_xml
    assert "2026-08-01 11:00:00" in sheet_xml
    assert "2026-08-01 00:30:00" in sheet_xml
    assert "退货" in workbook_xml


@pytest.mark.asyncio
async def test_ozon_return_export_uses_reviewed_status_translation():
    service = OzonReturnService()
    export_request = OzonReturnExportRequest(
        scope="selected",
        selected_keys=[OzonReturnKey(shop_id=9, return_id=1001, nm_id=2002)],
    )
    record = _record(
        status_display_name="На утилизации",
        status_display_name_cn="回收",
        status_sys_name=None,
    )

    with (
        patch(
            "kunpeng.services.ozon_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[9]),
        ),
        patch(
            "kunpeng.services.ozon_return_service."
            "crud_dwd_ozon_return_detail.list_returns_by_keys",
            new=AsyncMock(return_value=[record]),
        ),
        patch(
            "kunpeng.services.ozon_return_service.build_xlsx",
            return_value=b"workbook",
        ) as build_xlsx,
        patch(
            "kunpeng.services.ozon_return_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={9: "圣彼得堡店"}),
        ),
    ):
        content = await service.export_returns(
            AsyncMock(), user_id=3, export_request=export_request
        )

    assert content == b"workbook"
    exported_rows = build_xlsx.call_args.args[1]
    assert exported_rows[0]["status_display_name_cn"] == "处置中"
