from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import pytest

from kunpeng.schemas.wb_voc_question import (
    WBVOCQuestionExportRequest,
    WBVOCQuestionFilters,
    WBVOCQuestionItem,
    WBVOCQuestionKey,
)
from kunpeng.services.wb_voc_question_service import WBVOCQuestionService

EXPECTED_FIELDS = [
    "shop_id",
    "question_id",
    "created_date",
    "supplier_article",
    "nm_id",
    "brand_name",
    "text",
    "text_cn",
    "answer",
    "answer_cn",
]


def _record(**overrides):
    values = {
        "shop_id": 8,
        "question_id": "question-1",
        "created_date": datetime(2026, 7, 21, 8, 36, 17),
        "supplier_article": "article-1",
        "nm_id": 1214137012,
        "brand_name": "brand",
        "text": "适合大型犬吗？",
        "text_cn": "中文问题",
        "answer": "适合中大型犬。",
        "answer_cn": "中文回复",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_question_response_has_only_dwd_fields():
    assert list(WBVOCQuestionItem.model_fields) == EXPECTED_FIELDS


@pytest.mark.asyncio
async def test_list_questions_uses_moscow_date_bounds_and_serializes_time():
    service = WBVOCQuestionService()
    filters = WBVOCQuestionFilters(
        date_from=date(2026, 7, 21),
        date_to=date(2026, 7, 21),
        answer_status="answered",
    )

    with (
        patch(
            "kunpeng.services.wb_voc_question_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_question_service."
            "crud_dwd_wb_voc_question_detail.list_questions",
            new=AsyncMock(return_value=([_record()], 1)),
        ) as list_questions,
    ):
        response = await service.list_questions(
            AsyncMock(),
            user_id=3,
            filters=filters,
            page=1,
            page_size=20,
        )

    assert response.total == 1
    assert response.items[0].created_date.isoformat() == ("2026-07-21T11:36:17+03:00")
    kwargs = list_questions.await_args.kwargs
    assert kwargs["created_from"] == datetime(2026, 7, 20, 21, 0)
    assert kwargs["created_to"] == datetime(2026, 7, 21, 21, 0)
    assert kwargs["answer_status"] == "answered"


@pytest.mark.asyncio
async def test_selected_question_export_builds_xlsx_with_moscow_time():
    service = WBVOCQuestionService()
    export_request = WBVOCQuestionExportRequest(
        scope="selected",
        selected_keys=[WBVOCQuestionKey(shop_id=8, question_id="question-1")],
    )

    with (
        patch(
            "kunpeng.services.wb_voc_question_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_question_service.shop_crud.get_names_by_ids",
            new=AsyncMock(return_value={8: "测试店铺"}),
        ),
        patch(
            "kunpeng.services.wb_voc_question_service."
            "crud_dwd_wb_voc_question_detail.list_questions_by_keys",
            new=AsyncMock(return_value=[_record()]),
        ) as list_by_keys,
    ):
        content = await service.export_questions(
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
    assert "测试店铺" in sheet_xml
    assert "WB客户提问" in workbook_xml
