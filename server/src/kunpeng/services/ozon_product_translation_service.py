"""Translate Ozon product names once per shop and SKU, then reuse the cache."""

from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.dwd.ozon.product_name_translation import \
    crud_dwd_ozon_product_name_translation
from kunpeng.services.translation_service import (contains_cyrillic,
                                                  translate_to_chinese)
from kunpeng.utils.timezone import now_platform

_HAS_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


class OzonProductTranslationService:
    """Persist one automatic decision for each ``(shop_id, sku)`` key."""

    async def translate_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
    ) -> dict[str, Any]:
        candidates = await crud_dwd_ozon_product_name_translation.list_missing_products(
            db,
            shop_id=shop_id,
            limit=batch_size,
        )
        result = {
            "unique_products": len(candidates),
            "api_translations": 0,
            "cache_hits": 0,
            "passthrough": 0,
            "failed": 0,
            "pending": 0,
            "updated_dwd_rows": 0,
        }

        for candidate_shop_id, sku, source_name in candidates:
            cache = await crud_dwd_ozon_product_name_translation.get(
                db,
                shop_id=candidate_shop_id,
                sku=sku,
            )
            if cache is not None:
                if cache.product_name_cn:
                    result["cache_hits"] += 1
                    result[
                        "updated_dwd_rows"
                    ] += await crud_dwd_ozon_product_name_translation.apply_cached_name(
                        db,
                        shop_id=candidate_shop_id,
                        sku=sku,
                        product_name_cn=cache.product_name_cn,
                    )
                    continue
                elif cache.translation_status == "failed":
                    claimed = (
                        await (
                            crud_dwd_ozon_product_name_translation.claim_failed_retry(
                                db,
                                shop_id=candidate_shop_id,
                                sku=sku,
                            )
                        )
                    )
                    await db.commit()
                    if not claimed:
                        result["pending"] += 1
                        continue
                    source_name = cache.source_product_name
                else:
                    result["pending"] += 1
                    continue
            else:
                reserved = await crud_dwd_ozon_product_name_translation.reserve_once(
                    db,
                    shop_id=candidate_shop_id,
                    sku=sku,
                    source_product_name=source_name,
                )
                await db.commit()
                if not reserved:
                    result["pending"] += 1
                    continue

            translated_name: Optional[str]
            translation_source: Optional[str]
            if _HAS_CHINESE_RE.search(source_name) or not contains_cyrillic(
                source_name
            ):
                translated_name = source_name
                translation_source = "original"
                status = "passthrough"
                result["passthrough"] += 1
            else:
                translated_name = await translate_to_chinese(source_name)
                translation_source = "baidu" if translated_name else None
                status = "success" if translated_name else "failed"
                if translated_name:
                    result["api_translations"] += 1
                else:
                    result["failed"] += 1

            await crud_dwd_ozon_product_name_translation.complete(
                db,
                shop_id=candidate_shop_id,
                sku=sku,
                status=status,
                translated_name=translated_name,
                translation_source=translation_source,
                translated_at=now_platform().replace(tzinfo=None),
            )
            if translated_name:
                result[
                    "updated_dwd_rows"
                ] += await crud_dwd_ozon_product_name_translation.apply_cached_name(
                    db,
                    shop_id=candidate_shop_id,
                    sku=sku,
                    product_name_cn=translated_name,
                )
            await db.commit()

        return result

    async def translate_all_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 500,
        max_batches: int = 10,
    ) -> dict[str, Any]:
        """Drain bounded unique-product batches for current and historic rows."""
        totals: dict[str, Any] = {
            "batches": 0,
            "unique_products": 0,
            "api_translations": 0,
            "cache_hits": 0,
            "passthrough": 0,
            "failed": 0,
            "pending": 0,
            "updated_dwd_rows": 0,
            "stalled": False,
        }
        metric_keys = tuple(key for key in totals if key not in {"batches", "stalled"})
        for _ in range(max(1, max_batches)):
            result = await self.translate_missing(
                db, shop_id=shop_id, batch_size=batch_size
            )
            if result["unique_products"] == 0:
                break
            totals["batches"] += 1
            for key in metric_keys:
                totals[key] += result[key]
            if result["updated_dwd_rows"] == 0:
                totals["stalled"] = True
                break
        return totals


ozon_product_translation_service = OzonProductTranslationService()
