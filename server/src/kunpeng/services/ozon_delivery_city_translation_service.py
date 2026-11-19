"""Populate Chinese translations for Ozon order delivery cities."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.dwd.ozon.delivery_city_translation import \
    crud_dwd_ozon_delivery_city_translation
from kunpeng.services.translation_service import translate_dwd_value_to_chinese

# Stable place names are reviewed here so a generic machine translation cannot
# replace them with a literal or inconsistent rendering.
REVIEWED_OZON_DELIVERY_CITY_CN = {
    "Ангарск": "安加尔斯克",
    "Екатеринбург": "叶卡捷琳堡",
    "Иваново": "伊万诺沃",
    "Казань": "喀山",
    "Москва": "莫斯科",
    "Санкт-Петербург": "圣彼得堡",
    "Усолье-Сибирское": "乌索利耶-西伯利亚斯科耶",
}


class OzonDeliveryCityTranslationService:
    """Translate each distinct city once and reuse it across order rows."""

    async def translate_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
    ) -> dict[str, int]:
        cities = await crud_dwd_ozon_delivery_city_translation.list_missing_cities(
            db,
            shop_id=shop_id,
            limit=batch_size,
        )
        result = {
            "unique_cities": len(cities),
            "reviewed_hits": 0,
            "cache_hits": 0,
            "api_translations": 0,
            "failed": 0,
            "updated_dwd_rows": 0,
        }

        for city in cities:
            translated = REVIEWED_OZON_DELIVERY_CITY_CN.get(city.strip())
            if translated:
                result["reviewed_hits"] += 1
            else:
                translated = await crud_dwd_ozon_delivery_city_translation.get_existing_translation(
                    db,
                    delivery_city=city,
                )
                if translated:
                    result["cache_hits"] += 1
                else:
                    translated = await translate_dwd_value_to_chinese(city)
                    if translated:
                        result["api_translations"] += 1

            if not translated:
                result["failed"] += 1
                continue

            result[
                "updated_dwd_rows"
            ] += await crud_dwd_ozon_delivery_city_translation.apply_translation(
                db,
                delivery_city=city,
                delivery_city_cn=translated,
                shop_id=shop_id,
            )

        if result["updated_dwd_rows"]:
            await db.commit()
        return result

    async def translate_all_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
        max_batches: int = 10,
    ) -> dict[str, Any]:
        totals: dict[str, Any] = {
            "batches": 0,
            "unique_cities": 0,
            "reviewed_hits": 0,
            "cache_hits": 0,
            "api_translations": 0,
            "failed": 0,
            "updated_dwd_rows": 0,
            "stalled": False,
        }
        metric_keys = tuple(key for key in totals if key not in {"batches", "stalled"})
        for _ in range(max(1, max_batches)):
            result = await self.translate_missing(
                db,
                shop_id=shop_id,
                batch_size=batch_size,
            )
            if result["unique_cities"] == 0:
                break
            totals["batches"] += 1
            for key in metric_keys:
                totals[key] += result[key]
            if result["updated_dwd_rows"] == 0:
                totals["stalled"] = True
                break
        return totals


ozon_delivery_city_translation_service = OzonDeliveryCityTranslationService()
