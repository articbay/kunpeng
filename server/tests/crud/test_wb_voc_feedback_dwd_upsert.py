from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.voc_feedback import CRUDDWDWBVOCFeedbackDetail
from kunpeng.models.dwd.wildberries import DWDWBVOCFeedbackDetail


def test_wb_voc_feedback_dwd_model_has_only_confirmed_business_columns():
    assert list(DWDWBVOCFeedbackDetail.__table__.columns.keys()) == [
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
    assert DWDWBVOCFeedbackDetail.answer.comment == "回复正文"


@pytest.mark.asyncio
async def test_upsert_from_ods_uses_feedback_key_and_extracts_answer_text():
    crud = CRUDDWDWBVOCFeedbackDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 2
    upsert_result = Mock()
    upsert_result.rowcount = 3
    db.execute.side_effect = [count_result, upsert_result]

    result = await crud.upsert_from_ods(db, shop_id=8)

    assert result == {"source_count": 2, "affected_rows": 3}
    db.commit.assert_awaited_once()
    upsert_call = db.execute.await_args_list[1]
    statement = str(upsert_call.args[0])
    assert "ON DUPLICATE KEY UPDATE" in statement
    assert "json_unquote(json_extract" in statement.lower()
    assert "product_name AS source_product_name" in statement
    assert "product_name_cn = IF(" in statement
    assert "VALUES(" not in statement
    assert upsert_call.args[1] == {"shop_id": 8}


@pytest.mark.asyncio
async def test_upsert_from_empty_ods_does_not_write():
    crud = CRUDDWDWBVOCFeedbackDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.commit.assert_not_awaited()
