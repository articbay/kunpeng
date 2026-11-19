from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.wb_return import (
    WBReturnExportRequest,
    WBReturnFilters,
    WBReturnItem,
    WBReturnKey,
)
from kunpeng.services.wb_return_service import WBReturnService

EXPECTED_FIELDS = [
    "shop_id",
    "brand",
    "subject_name",
    "subject_name_cn",
    "barcode_ori",
    "barcode_hand",
    "nm_id",
    "sticker_id",
    "status",
    "status_cn",
    "ready_to_return_dt",
    "completed_dt",
    "expired_dt",
    "return_type",
    "return_type_cn",
    "order_dt",
    "reason",
    "reason_cn",
    "order_id",
    "srid",
    "dst_office_address",
    "dst_office_address_cn",
    "dst_office_id",
]


def _record(**overrides):
    values = {
        "shop_id": 8,
        "brand": "brand",
        "subject_name": "subject",
        "subject_name_cn": "商品品类",
        "barcode_ori": "2044420598851",
        "barcode_hand": "TG-HC02904",
        "nm_id": 1214137012,
        "sticker_id": "sticker-1",
        "status": "raw-status",
        "status_cn": "状态",
        "ready_to_return_dt": datetime(2026, 7, 21, 8, 36, 17),
        "completed_dt": datetime(2026, 7, 22, 9, 10, 0),
        "expired_dt": None,
        "return_type": "raw-return-type",
        "return_type_cn": "退货类型",
        "order_dt": date(2026, 7, 21),
        "reason": "reason",
        "reason_cn": "退货原因",
        "order_id": 123456,
        "srid": "srid-1",
        "dst_office_address": "address",
        "dst_office_address_cn": "地址",
        "dst_office_id": 789,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_return_response_has_only_dwd_fields():
    assert list(WBReturnItem.model_fields) == EXPECTED_FIELDS


@pytest.mark.asyncio
async def test_list_returns_passes_order_dt_bounds_and_serializes_times():
    service = WBReturnService()
    filters = WBReturnFilters(
        date_from=date(2026, 7, 20),
        date_to=date(2026, 7, 21),
        status="raw-status",
    )

    with (
        patch(
            "kunpeng.services.wb_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_return_service."
            "crud_dwd_wb_return_detail.list_returns",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_returns,
    ):
        response = await service.list_returns(
            AsyncMock(),
            user_id=3,
            filters=filters,
            page=1,
            page_size=20,
        )

    assert response.total == 1
    assert response.items[0].ready_to_return_dt.isoformat() == (
        "2026-07-21T11:36:17+03:00"
    )
    assert response.items[0].order_dt == date(2026, 7, 21)
    kwargs = list_returns.await_args.kwargs
    assert kwargs["date_from"] == date(2026, 7, 20)
    assert kwargs["date_to"] == date(2026, 7, 21)
    assert kwargs["status"] == "raw-status"


@pytest.mark.asyncio
async def test_selected_return_export_builds_xlsx_with_moscow_times():
    service = WBReturnService()
    export_request = WBReturnExportRequest(
        scope="selected",
        selected_keys=[WBReturnKey(shop_id=8, srid="srid-1")],
    )

    with (
        patch(
            "kunpeng.services.wb_return_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_return_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={8: "测试店铺"}),
        ),
        patch(
            "kunpeng.services.wb_return_service."
            "crud_dwd_wb_return_detail.list_returns_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
    ):
        content = await service.export_returns(
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
    assert "2026-07-22 12:10:00" in sheet_xml
    assert "2026-07-21" in sheet_xml
    assert "测试店铺" in sheet_xml
    assert "WB退货" in workbook_xml
