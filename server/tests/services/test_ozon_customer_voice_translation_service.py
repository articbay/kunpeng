from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.services.ozon_customer_voice_translation_service import \
    OzonCustomerVoiceTranslationService


@pytest.mark.asyncio
async def test_translate_missing_selects_every_nonempty_missing_source():
    service = OzonCustomerVoiceTranslationService()
    result_proxy = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    db = SimpleNamespace(
        execute=AsyncMock(return_value=result_proxy), commit=AsyncMock()
    )

    result = await service.translate_missing(db, shop_id=2, batch_size=200)

    query = db.execute.await_args.args[0]
    sql = str(query.compile(dialect=mysql.dialect()))
    assert "REGEXP" not in sql
    assert result == {"processed_rows": 0, "translated_fields": 0}


@pytest.mark.asyncio
async def test_translate_missing_maps_customer_voice_status_codes():
    service = OzonCustomerVoiceTranslationService()
    row = SimpleNamespace(
        product_name=None,
        product_name_cn=None,
        order_status="DELIVERED",
        order_status_cn=None,
        review_text=None,
        review_text_cn=None,
        review_status="UNPROCESSED",
        review_status_cn=None,
    )
    result_proxy = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [row]))
    db = SimpleNamespace(
        execute=AsyncMock(return_value=result_proxy), commit=AsyncMock()
    )

    with patch(
        "kunpeng.services.ozon_customer_voice_translation_service."
        "translate_dwd_value_to_chinese",
        new=AsyncMock(side_effect=["已送达", "未处理"]),
    ) as translate:
        result = await service.translate_missing(db, shop_id=2, batch_size=200)

    assert row.order_status_cn == "已送达"
    assert row.review_status_cn == "未处理"
    assert result == {"processed_rows": 1, "translated_fields": 2}
    assert translate.await_count == 2


@pytest.mark.asyncio
async def test_translate_all_missing_drains_multiple_batches():
    service = OzonCustomerVoiceTranslationService()
    service.translate_missing = AsyncMock(
        side_effect=[
            {"processed_rows": 200, "translated_fields": 350},
            {"processed_rows": 12, "translated_fields": 20},
            {"processed_rows": 0, "translated_fields": 0},
        ]
    )

    result = await service.translate_all_missing(
        SimpleNamespace(), shop_id=2, batch_size=200, max_batches=10
    )

    assert result == {
        "batches": 2,
        "processed_rows": 212,
        "translated_fields": 370,
        "stalled": False,
    }


@pytest.mark.asyncio
async def test_translate_all_missing_stops_when_api_makes_no_progress():
    service = OzonCustomerVoiceTranslationService()
    service.translate_missing = AsyncMock(
        return_value={"processed_rows": 5, "translated_fields": 0}
    )

    result = await service.translate_all_missing(
        SimpleNamespace(), shop_id=2, batch_size=200, max_batches=10
    )

    assert result["batches"] == 1
    assert result["stalled"] is True
    service.translate_missing.assert_awaited_once()
