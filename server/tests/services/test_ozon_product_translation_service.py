from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.dwd.ozon.product_name_translation import \
    crud_dwd_ozon_product_name_translation
from kunpeng.services.ozon_product_translation_service import (
    OzonProductTranslationService, ozon_product_translation_service)


class FakeDb:
    def __init__(self):
        self.commit_count = 0

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_translate_all_missing_drains_unique_product_batches():
    service = OzonProductTranslationService()
    service.translate_missing = AsyncMock(
        side_effect=[
            {
                "unique_products": 2,
                "api_translations": 1,
                "cache_hits": 1,
                "passthrough": 0,
                "failed": 0,
                "pending": 0,
                "updated_dwd_rows": 4,
            },
            {
                "unique_products": 0,
                "api_translations": 0,
                "cache_hits": 0,
                "passthrough": 0,
                "failed": 0,
                "pending": 0,
                "updated_dwd_rows": 0,
            },
        ]
    )

    result = await service.translate_all_missing(
        SimpleNamespace(), shop_id=7, batch_size=500, max_batches=10
    )

    assert result["batches"] == 1
    assert result["unique_products"] == 2
    assert result["updated_dwd_rows"] == 4
    assert result["stalled"] is False


@pytest.mark.asyncio
async def test_russian_name_is_translated_and_applied_once(monkeypatch):
    db = FakeDb()
    list_missing = AsyncMock(return_value=[(7, 123, "Ошейник для собак")])
    get_cache = AsyncMock(return_value=None)
    reserve = AsyncMock(return_value=True)
    complete = AsyncMock()
    apply_name = AsyncMock(return_value=3)
    translate = AsyncMock(return_value="狗项圈")

    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        list_missing,
    )
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "get", get_cache)
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "reserve_once", reserve)
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "complete", complete)
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation, "apply_cached_name", apply_name
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    result = await ozon_product_translation_service.translate_missing(db, shop_id=7)

    translate.assert_awaited_once_with("Ошейник для собак")
    reserve.assert_awaited_once_with(
        db,
        shop_id=7,
        sku=123,
        source_product_name="Ошейник для собак",
    )
    assert complete.await_args.kwargs["status"] == "success"
    apply_name.assert_awaited_once_with(
        db, shop_id=7, sku=123, product_name_cn="狗项圈"
    )
    assert result["api_translations"] == 1
    assert result["updated_dwd_rows"] == 3
    assert db.commit_count == 2


@pytest.mark.asyncio
async def test_existing_shop_sku_cache_is_reused_without_api_call(monkeypatch):
    db = FakeDb()
    cache = SimpleNamespace(product_name_cn="狗项圈", translation_status="success")
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        AsyncMock(return_value=[(7, 123, "Ошейник для собак")]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "get",
        AsyncMock(return_value=cache),
    )
    reserve = AsyncMock()
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "reserve_once", reserve)
    apply_name = AsyncMock(return_value=2)
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation, "apply_cached_name", apply_name
    )
    translate = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    result = await ozon_product_translation_service.translate_missing(db)

    translate.assert_not_awaited()
    reserve.assert_not_awaited()
    apply_name.assert_awaited_once_with(
        db, shop_id=7, sku=123, product_name_cn="狗项圈"
    )
    assert result["cache_hits"] == 1
    assert result["updated_dwd_rows"] == 2


@pytest.mark.asyncio
async def test_same_sku_in_two_shops_has_independent_cache_keys(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        AsyncMock(
            return_value=[
                (7, 123, "Ошейник для собак"),
                (8, 123, "Ошейник для собак"),
            ]
        ),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "get",
        AsyncMock(return_value=None),
    )
    reserve = AsyncMock(return_value=True)
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "reserve_once", reserve)
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "complete", AsyncMock())
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "apply_cached_name",
        AsyncMock(return_value=1),
    )
    translate = AsyncMock(return_value="狗项圈")
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    await ozon_product_translation_service.translate_missing(db)

    assert translate.await_count == 2
    assert [call.kwargs["shop_id"] for call in reserve.await_args_list] == [7, 8]


@pytest.mark.asyncio
async def test_non_cyrillic_name_is_cached_as_passthrough(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        AsyncMock(return_value=[(7, 456, "Collar Model X")]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "get",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "reserve_once",
        AsyncMock(return_value=True),
    )
    complete = AsyncMock()
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "complete", complete)
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "apply_cached_name",
        AsyncMock(return_value=1),
    )
    translate = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    result = await ozon_product_translation_service.translate_missing(db)

    translate.assert_not_awaited()
    assert complete.await_args.kwargs["status"] == "passthrough"
    assert complete.await_args.kwargs["translation_source"] == "original"
    assert result["passthrough"] == 1


@pytest.mark.asyncio
async def test_failed_cache_is_atomically_claimed_and_retried(monkeypatch):
    db = FakeDb()
    cache = SimpleNamespace(
        product_name_cn=None,
        translation_status="failed",
        source_product_name="Ошейник для собак",
        attempt_count=1,
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        AsyncMock(return_value=[(7, 123, "newer source name")]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "get",
        AsyncMock(return_value=cache),
    )
    claim = AsyncMock(return_value=True)
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation, "claim_failed_retry", claim
    )
    reserve = AsyncMock()
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "reserve_once", reserve)
    complete = AsyncMock()
    monkeypatch.setattr(crud_dwd_ozon_product_name_translation, "complete", complete)
    apply_name = AsyncMock(return_value=1)
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation, "apply_cached_name", apply_name
    )
    translate = AsyncMock(return_value="狗项圈")
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    result = await ozon_product_translation_service.translate_missing(db)

    claim.assert_awaited_once_with(db, shop_id=7, sku=123)
    reserve.assert_not_awaited()
    translate.assert_awaited_once_with("Ошейник для собак")
    assert complete.await_args.kwargs["status"] == "success"
    assert result["api_translations"] == 1
    assert result["updated_dwd_rows"] == 1
    assert db.commit_count == 2


@pytest.mark.asyncio
async def test_failed_cache_is_not_translated_when_retry_claim_is_lost(monkeypatch):
    db = FakeDb()
    cache = SimpleNamespace(
        product_name_cn=None,
        translation_status="failed",
        source_product_name="Ошейник для собак",
        attempt_count=1,
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "list_missing_products",
        AsyncMock(return_value=[(7, 123, "Ошейник для собак")]),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "get",
        AsyncMock(return_value=cache),
    )
    monkeypatch.setattr(
        crud_dwd_ozon_product_name_translation,
        "claim_failed_retry",
        AsyncMock(return_value=False),
    )
    translate = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_product_translation_service.translate_to_chinese",
        translate,
    )

    result = await ozon_product_translation_service.translate_missing(db)

    translate.assert_not_awaited()
    assert result["pending"] == 1
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_candidate_query_allows_only_bounded_failed_retries():
    class EmptyResult:
        def all(self):
            return []

    class CaptureDb:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return EmptyResult()

    db = CaptureDb()
    await crud_dwd_ozon_product_name_translation.list_missing_products(db)
    sql = str(
        db.statement.compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "NOT (EXISTS" in sql
    assert "dwd_ozon_product_name_translation_cache" in sql
    assert "translation_status != 'failed'" in sql
    assert "attempt_count >= 3" in sql
