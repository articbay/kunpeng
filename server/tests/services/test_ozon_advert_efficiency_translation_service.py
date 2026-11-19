from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kunpeng.services.ozon_advert_efficiency_translation_service import \
    OzonAdvertEfficiencyTranslationService


@pytest.mark.asyncio
async def test_translate_all_missing_drains_multiple_advert_batches():
    service = OzonAdvertEfficiencyTranslationService()
    service.translate_missing = AsyncMock(
        side_effect=[
            {
                "product_candidates": 2,
                "translated_products": 2,
                "category_candidates": 1,
                "translated_categories": 1,
            },
            {
                "product_candidates": 0,
                "translated_products": 0,
                "category_candidates": 0,
                "translated_categories": 0,
            },
        ]
    )

    result = await service.translate_all_missing(
        SimpleNamespace(), shop_id=7, batch_size=200, max_batches=10
    )

    assert result == {
        "batches": 1,
        "product_candidates": 2,
        "translated_products": 2,
        "category_candidates": 1,
        "translated_categories": 1,
        "stalled": False,
    }
