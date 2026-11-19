from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.wb_voc_feedback import (
    WBVOCFeedbackExportRequest,
    WBVOCFeedbackFilters,
    WBVOCFeedbackItem,
    WBVOCFeedbackKey,
)
from kunpeng.services.wb_voc_feedback_service import (
    FEEDBACK_EXPORT_COLUMNS,
    WBVOCFeedbackService,
)

EXPECTED_FIELDS = [
    "shop_id",
    "feedback_id",
    "created_date",
    "supplier_article",
    "nm_id",
    "product_name",
    "product_name_cn",
    "product_valuation",
    "brand_name",
    "text",
    "text_cn",
    "pros",
    "pros_cn",
    "cons",
    "cons_cn",
    "user_name",
    "color",
    "color_cn",
    "size",
    "size_cn",
    "answer",
    "answer_cn",
    "parent_feedback_id",
    "child_feedback_id",
]


def test_feedback_export_places_shop_name_after_shop_id():
    assert FEEDBACK_EXPORT_COLUMNS[:2] == (
        ("店铺ID", "shop_id"),
        ("店铺名称", "shop_name"),
    )


def _record(**overrides):
    values = {
        "shop_id": 8,
        "feedback_id": "feedback-1",
        "created_date": datetime(2026, 7, 21, 8, 36, 17),
        "supplier_article": "article-1",
        "nm_id": 1214137012,
        "product_name": "Поводок для собак",
        "product_name_cn": "狗牵引绳",
        "product_valuation": 5,
        "brand_name": "brand",
        "text": "正文",
        "text_cn": "中文正文",
        "pros": "优点",
        "pros_cn": "中文优点",
        "cons": "缺点",
        "cons_cn": "中文缺点",
        "user_name": "用户",
        "color": "橙色",
        "color_cn": "橙色中文",
        "size": "0",
        "size_cn": "零码",
        "answer": "回复",
        "answer_cn": "中文回复",
        "parent_feedback_id": None,
        "child_feedback_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_feedback_response_has_only_dwd_fields():
    assert list(WBVOCFeedbackItem.model_fields) == EXPECTED_FIELDS


@pytest.mark.asyncio
async def test_list_feedbacks_uses_moscow_date_bounds_and_serializes_time():
    service = WBVOCFeedbackService()
    filters = WBVOCFeedbackFilters(
        date_from=date(2026, 7, 21),
        date_to=date(2026, 7, 21),
        product_valuations=[5],
    )

    with (
        patch(
            "kunpeng.services.wb_voc_feedback_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_feedback_service."
            "crud_dwd_wb_voc_feedback_detail.list_feedbacks",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_feedbacks,
    ):
        response = await service.list_feedbacks(
            AsyncMock(),
            user_id=3,
            filters=filters,
            page=1,
            page_size=20,
        )

    assert response.total == 1
    assert response.items[0].created_date.isoformat() == ("2026-07-21T11:36:17+03:00")
    kwargs = list_feedbacks.await_args.kwargs
    assert kwargs["created_from"] == datetime(2026, 7, 20, 21, 0)
    assert kwargs["created_to"] == datetime(2026, 7, 21, 21, 0)
    assert kwargs["product_valuations"] == [5]


@pytest.mark.asyncio
async def test_selected_export_builds_xlsx_with_moscow_time():
    service = WBVOCFeedbackService()
    export_request = WBVOCFeedbackExportRequest(
        scope="selected",
        selected_keys=[WBVOCFeedbackKey(shop_id=8, feedback_id="feedback-1")],
    )

    with (
        patch(
            "kunpeng.services.wb_voc_feedback_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_feedback_service."
            "crud_dwd_wb_voc_feedback_detail.list_feedbacks_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
        patch(
            "kunpeng.services.wb_voc_feedback_service." "shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={8: "WB测试店铺"}),
        ),
    ):
        content = await service.export_feedbacks(
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
    assert "Поводок для собак" in sheet_xml
    assert "狗牵引绳" in sheet_xml
    assert "WB客户评价" in workbook_xml
