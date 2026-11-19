from unittest.mock import AsyncMock, patch

import pytest

from kunpeng.services import translation_service


def test_contains_cyrillic_only_matches_cyrillic_values():
    assert translation_service.contains_cyrillic("Склад Коледино") is True
    assert translation_service.contains_cyrillic("Kolodino 仓库") is False
    assert translation_service.contains_cyrillic(None) is False


@pytest.mark.asyncio
async def test_translate_dwd_value_uses_mapping_and_passthrough_rules():
    mapping = {"DELIVERED": "已送达"}

    assert (
        await translation_service.translate_dwd_value_to_chinese(
            "delivered", fixed_mapping=mapping
        )
        == "已送达"
    )
    assert await translation_service.translate_dwd_value_to_chinese("中文") == "中文"
    assert await translation_service.translate_dwd_value_to_chinese("XL") == "XL"
    assert await translation_service.translate_dwd_value_to_chinese("42") == "42"


@pytest.mark.asyncio
async def test_translate_dwd_value_auto_translates_english_prose():
    translation_service._TRANSLATION_CACHE.clear()
    with patch.object(
        translation_service,
        "_translate_via_baidu",
        new=AsyncMock(return_value="黑色项圈"),
    ) as translate:
        result = await translation_service.translate_dwd_value_to_chinese(
            "Black dog collar"
        )

    assert result == "黑色项圈"
    translate.assert_awaited_once_with(
        "Black dog collar", timeout=15.0, source_language="auto"
    )


@pytest.mark.asyncio
async def test_translate_to_chinese_uses_baidu_and_caches_result():
    translation_service._TRANSLATION_CACHE.clear()
    with patch.object(
        translation_service,
        "_translate_via_baidu",
        new=AsyncMock(return_value="科列季诺仓库"),
    ) as translate:
        first = await translation_service.translate_to_chinese("Склад Коледино")
        second = await translation_service.translate_to_chinese("Склад Коледино")

    assert first == second == "科列季诺仓库"
    translate.assert_awaited_once_with("Склад Коледино", timeout=15.0)


@pytest.mark.asyncio
async def test_translate_to_chinese_ignores_non_cyrillic_values():
    with patch.object(
        translation_service,
        "_translate_via_baidu",
        new=AsyncMock(),
    ) as translate:
        result = await translation_service.translate_to_chinese("warehouse")

    assert result is None
    translate.assert_not_awaited()


@pytest.mark.asyncio
async def test_baidu_retryable_error_uses_backoff_then_succeeds():
    request = AsyncMock(
        side_effect=[
            {"error_code": "54003", "error_msg": "frequency limited"},
            {"trans_result": [{"dst": "狗项圈"}]},
        ]
    )
    sleep = AsyncMock()
    with (
        patch.object(translation_service.settings, "baidu_translate_app_id", "id"),
        patch.object(
            translation_service.settings, "baidu_translate_secret_key", "secret"
        ),
        patch.object(
            translation_service,
            "_request_baidu_translation",
            new=request,
        ),
        patch.object(translation_service.asyncio, "sleep", new=sleep),
    ):
        result = await translation_service._translate_via_baidu("Ошейник", timeout=15.0)

    assert result == "狗项圈"
    assert request.await_count == 2
    sleep.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_baidu_permanent_error_is_not_retried():
    request = AsyncMock(
        return_value={"error_code": "54001", "error_msg": "invalid signature"}
    )
    sleep = AsyncMock()
    with (
        patch.object(translation_service.settings, "baidu_translate_app_id", "id"),
        patch.object(
            translation_service.settings, "baidu_translate_secret_key", "secret"
        ),
        patch.object(
            translation_service,
            "_request_baidu_translation",
            new=request,
        ),
        patch.object(translation_service.asyncio, "sleep", new=sleep),
    ):
        result = await translation_service._translate_via_baidu("Ошейник", timeout=15.0)

    assert result is None
    request.assert_awaited_once_with("Ошейник", timeout=15.0)
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_baidu_empty_result_is_retried():
    request = AsyncMock(
        side_effect=[
            {"trans_result": []},
            {"trans_result": [{"dst": "狗项圈"}]},
        ]
    )
    sleep = AsyncMock()
    with (
        patch.object(translation_service.settings, "baidu_translate_app_id", "id"),
        patch.object(
            translation_service.settings, "baidu_translate_secret_key", "secret"
        ),
        patch.object(
            translation_service,
            "_request_baidu_translation",
            new=request,
        ),
        patch.object(translation_service.asyncio, "sleep", new=sleep),
    ):
        result = await translation_service._translate_via_baidu("Ошейник", timeout=15.0)

    assert result == "狗项圈"
    assert request.await_count == 2
    sleep.assert_awaited_once_with(1)
