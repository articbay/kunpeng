from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kunpeng.models.dwd.wildberries import (
    DWDWBOrderDetail,
    DWDWBVOCFeedbackDetail,
    DWDWBVOCQuestionDetail,
)
from kunpeng.services.wb_dwd_translation_service import (
    WB_DWD_TRANSLATION_SPECS,
    WBDWDTranslationService,
)


@pytest.mark.asyncio
async def test_translate_model_populates_every_nonempty_missing_value():
    record = SimpleNamespace(
        text="Подойдет для крупной собаки?",
        text_cn=None,
        answer="Already translated",
        answer_cn=None,
    )
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [record]
    db = AsyncMock()
    db.execute.return_value = scalar_result
    service = WBDWDTranslationService()

    with patch(
        "kunpeng.services.wb_dwd_translation_service." "translate_dwd_value_to_chinese",
        new=AsyncMock(side_effect=["适合大型犬吗？", "已翻译"]),
    ) as translate:
        result = await service._translate_model(
            db,
            model=DWDWBVOCQuestionDetail,
            field_pairs=(("text", "text_cn"), ("answer", "answer_cn")),
            shop_id=8,
            batch_size=50,
        )

    assert record.text_cn == "适合大型犬吗？"
    assert record.answer_cn == "已翻译"
    assert translate.await_count == 2
    db.commit.assert_awaited_once()
    assert result == {
        "scanned_rows": 1,
        "translated_values": 2,
        "failed_values": 0,
    }


@pytest.mark.asyncio
async def test_translate_model_uses_reviewed_wb_order_status_without_api_call():
    record = SimpleNamespace(wb_status="sorted", wb_status_cn=None)
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [record]
    db = AsyncMock()
    db.execute.return_value = scalar_result
    service = WBDWDTranslationService()

    with patch(
        "kunpeng.services.wb_dwd_translation_service." "translate_dwd_value_to_chinese",
        new=AsyncMock(),
    ) as translate:
        result = await service._translate_model(
            db,
            model=DWDWBOrderDetail,
            field_pairs=(("wb_status", "wb_status_cn"),),
            shop_id=8,
            batch_size=50,
        )

    assert record.wb_status_cn == "WB已接收并分拣"
    translate.assert_not_awaited()
    db.commit.assert_awaited_once()
    assert result == {
        "scanned_rows": 1,
        "translated_values": 1,
        "failed_values": 0,
    }


@pytest.mark.asyncio
async def test_translate_model_uses_reviewed_supplier_status_without_api_call():
    record = SimpleNamespace(supplier_status="confirm", supplier_status_cn=None)
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [record]
    db = AsyncMock()
    db.execute.return_value = scalar_result
    service = WBDWDTranslationService()

    with patch(
        "kunpeng.services.wb_dwd_translation_service." "translate_dwd_value_to_chinese",
        new=AsyncMock(),
    ) as translate:
        result = await service._translate_model(
            db,
            model=DWDWBOrderDetail,
            field_pairs=(("supplier_status", "supplier_status_cn"),),
            shop_id=8,
            batch_size=50,
        )

    assert record.supplier_status_cn == "组装中"
    translate.assert_not_awaited()
    db.commit.assert_awaited_once()
    assert result == {
        "scanned_rows": 1,
        "translated_values": 1,
        "failed_values": 0,
    }


@pytest.mark.asyncio
async def test_translate_model_populates_feedback_product_name_cn():
    record = SimpleNamespace(
        product_name="Поводок для собак",
        product_name_cn=None,
    )
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [record]
    db = AsyncMock()
    db.execute.return_value = scalar_result
    service = WBDWDTranslationService()

    with patch(
        "kunpeng.services.wb_dwd_translation_service." "translate_dwd_value_to_chinese",
        new=AsyncMock(return_value="狗牵引绳"),
    ) as translate:
        result = await service._translate_model(
            db,
            model=DWDWBVOCFeedbackDetail,
            field_pairs=(("product_name", "product_name_cn"),),
            shop_id=8,
            batch_size=50,
        )

    assert record.product_name_cn == "狗牵引绳"
    translate.assert_awaited_once_with("Поводок для собак")
    db.commit.assert_awaited_once()
    assert result == {
        "scanned_rows": 1,
        "translated_values": 1,
        "failed_values": 0,
    }


@pytest.mark.asyncio
async def test_translate_all_missing_drains_batches_until_empty():
    service = WBDWDTranslationService()
    first_tables = {
        model.__tablename__: {
            "scanned_rows": 1,
            "translated_values": 1,
            "failed_values": 0,
        }
        for model, _ in WB_DWD_TRANSLATION_SPECS
    }
    empty_tables = {
        table_name: {
            "scanned_rows": 0,
            "translated_values": 0,
            "failed_values": 0,
        }
        for table_name in first_tables
    }

    with patch.object(
        service,
        "translate_missing",
        new=AsyncMock(side_effect=[{"tables": first_tables}, {"tables": empty_tables}]),
    ) as translate_missing:
        result = await service.translate_all_missing(AsyncMock())

    assert translate_missing.await_count == 2
    assert result["batches"] == 2
    assert result["completed"] is True
    assert result["stalled"] is False
    assert all(
        table_result["translated_values"] == 1
        for table_result in result["tables"].values()
    )
