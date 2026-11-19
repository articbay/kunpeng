from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.voc_question import CRUDDWDWBVOCQuestionDetail
from kunpeng.models.dwd.wildberries import DWDWBVOCQuestionDetail


def test_wb_voc_question_dwd_model_has_only_confirmed_business_columns():
    assert list(DWDWBVOCQuestionDetail.__table__.columns.keys()) == [
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
    assert DWDWBVOCQuestionDetail.answer.comment == "回复"


@pytest.mark.asyncio
async def test_upsert_from_ods_uses_question_key_and_extracts_answer_text():
    crud = CRUDDWDWBVOCQuestionDetail()
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
    assert "VALUES(" not in statement
    assert upsert_call.args[1] == {"shop_id": 8}


@pytest.mark.asyncio
async def test_upsert_from_empty_ods_does_not_write():
    crud = CRUDDWDWBVOCQuestionDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.commit.assert_not_awaited()
