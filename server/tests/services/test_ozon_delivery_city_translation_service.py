from unittest.mock import AsyncMock

import pytest

from kunpeng.crud.dwd.ozon.delivery_city_translation import \
    crud_dwd_ozon_delivery_city_translation
from kunpeng.services.ozon_delivery_city_translation_service import \
    OzonDeliveryCityTranslationService


class FakeDb:
    def __init__(self):
        self.commit_count = 0

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_reviewed_city_is_applied_without_api_call(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "list_missing_cities",
        AsyncMock(return_value=["Москва"]),
    )
    existing = AsyncMock()
    apply_translation = AsyncMock(return_value=12)
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "get_existing_translation",
        existing,
    )
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "apply_translation",
        apply_translation,
    )
    translate = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_delivery_city_translation_service."
        "translate_dwd_value_to_chinese",
        translate,
    )

    result = await OzonDeliveryCityTranslationService().translate_missing(
        db,
        shop_id=7,
    )

    existing.assert_not_awaited()
    translate.assert_not_awaited()
    apply_translation.assert_awaited_once_with(
        db,
        delivery_city="Москва",
        delivery_city_cn="莫斯科",
        shop_id=7,
    )
    assert result["reviewed_hits"] == 1
    assert result["updated_dwd_rows"] == 12
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_existing_dwd_translation_is_reused_before_api(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "list_missing_cities",
        AsyncMock(return_value=["Тула"]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "get_existing_translation",
        AsyncMock(return_value="图拉"),
    )
    apply_translation = AsyncMock(return_value=3)
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "apply_translation",
        apply_translation,
    )
    translate = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_delivery_city_translation_service."
        "translate_dwd_value_to_chinese",
        translate,
    )

    result = await OzonDeliveryCityTranslationService().translate_missing(db)

    translate.assert_not_awaited()
    apply_translation.assert_awaited_once_with(
        db,
        delivery_city="Тула",
        delivery_city_cn="图拉",
        shop_id=None,
    )
    assert result["cache_hits"] == 1
    assert result["updated_dwd_rows"] == 3


@pytest.mark.asyncio
async def test_unseen_city_uses_baidu_fallback_once_for_all_rows(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "list_missing_cities",
        AsyncMock(return_value=["Тула"]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "get_existing_translation",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_delivery_city_translation,
        "apply_translation",
        AsyncMock(return_value=25),
    )
    translate = AsyncMock(return_value="图拉")
    monkeypatch.setattr(
        "kunpeng.services.ozon_delivery_city_translation_service."
        "translate_dwd_value_to_chinese",
        translate,
    )

    result = await OzonDeliveryCityTranslationService().translate_missing(db)

    translate.assert_awaited_once_with("Тула")
    assert result["api_translations"] == 1
    assert result["updated_dwd_rows"] == 25
