from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from kunpeng.models.dwd.wildberries import (DWDWBReturnDetail,
                                            DWDWBVOCFeedbackDetail,
                                            DWDWBVOCQuestionDetail)
from kunpeng.schemas.wb_voc_pivot import (WBVOCPivotExportRequest,
                                          WBVOCPivotFilters)
from kunpeng.services.wb_voc_pivot_service import WBVOCPivotService


@pytest.mark.asyncio
async def test_export_reads_three_dwd_sources_without_database_writes():
    service = WBVOCPivotService()
    db = AsyncMock()
    request = WBVOCPivotExportRequest(
        filters=WBVOCPivotFilters(
            shop_id=8,
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            nm_id=419767432,
        )
    )
    feedback = DWDWBVOCFeedbackDetail(
        shop_id=8,
        feedback_id="feedback-1",
        created_date=datetime(2026, 7, 21, 8, 0),
        nm_id=419767432,
        product_valuation=5,
    )
    question = DWDWBVOCQuestionDetail(
        shop_id=8,
        question_id="question-1",
        created_date=datetime(2026, 7, 21, 9, 0),
        nm_id=419767432,
    )
    returned = DWDWBReturnDetail(
        shop_id=8,
        srid="return-1",
        order_dt=date(2026, 7, 20),
        nm_id=419767432,
        status="Выдано",
    )

    with (
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_voc_feedback_detail.list_feedbacks_for_export",
            new=AsyncMock(return_value=[feedback]),
        ) as feedback_query,
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_voc_question_detail.list_questions_for_export",
            new=AsyncMock(return_value=[question]),
        ) as question_query,
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_return_detail.list_returns_for_export",
            new=AsyncMock(return_value=[returned]),
        ) as return_query,
    ):
        content = await service.export_workbook(db, user_id=3, export_request=request)

    assert content.startswith(b"PK")
    feedback_query.assert_awaited_once()
    question_query.assert_awaited_once()
    return_query.assert_awaited_once()
    db.add.assert_not_called()
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_supplier_article_filter_skips_returns_without_that_column():
    service = WBVOCPivotService()
    db = AsyncMock()
    request = WBVOCPivotExportRequest(
        filters=WBVOCPivotFilters(supplier_article="seller-article")
    )

    with (
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "shop_crud.get_accessible_ids_by_user_platform",
            new=AsyncMock(return_value=[8]),
        ),
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_voc_feedback_detail.list_feedbacks_for_export",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_voc_question_detail.list_questions_for_export",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "kunpeng.services.wb_voc_pivot_service."
            "crud_dwd_wb_return_detail.list_returns_for_export",
            new=AsyncMock(return_value=[]),
        ) as return_query,
    ):
        content = await service.export_workbook(db, user_id=3, export_request=request)

    assert content.startswith(b"PK")
    return_query.assert_not_awaited()
