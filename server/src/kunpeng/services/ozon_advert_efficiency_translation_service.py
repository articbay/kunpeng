"""Translate missing Ozon advertising product and category names."""

from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon.advert_efficiency import \
    DWDOzonAdvertEfficiencyDetail
from kunpeng.services.translation_service import translate_dwd_value_to_chinese


class OzonAdvertEfficiencyTranslationService:
    """Fill translation columns by unique business keys to reduce API calls."""

    async def translate_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
    ) -> dict[str, int]:
        model = DWDOzonAdvertEfficiencyDetail
        limit = max(1, min(batch_size, 500))

        product_query = (
            select(
                model.shop_id, model.sku, func.max(model.product_name).label("source")
            )
            .where(
                model.product_name.is_not(None),
                func.trim(model.product_name) != "",
                or_(
                    model.product_name_cn.is_(None),
                    func.trim(model.product_name_cn) == "",
                ),
            )
            .group_by(model.shop_id, model.sku)
            .order_by(model.shop_id, model.sku)
            .limit(limit)
        )
        if shop_id is not None:
            product_query = product_query.where(model.shop_id == shop_id)
        products = list((await db.execute(product_query)).all())

        translated_products = 0
        for row in products:
            translated = await translate_dwd_value_to_chinese(row.source)
            if not translated:
                continue
            await db.execute(
                update(model)
                .where(
                    model.shop_id == row.shop_id,
                    model.sku == row.sku,
                    or_(
                        model.product_name_cn.is_(None),
                        func.trim(model.product_name_cn) == "",
                    ),
                )
                .values(product_name_cn=translated)
            )
            translated_products += 1

        category_query = (
            select(model.shop_id, model.category_name.label("source"))
            .where(
                model.category_name.is_not(None),
                func.trim(model.category_name) != "",
                or_(
                    model.category_name_cn.is_(None),
                    func.trim(model.category_name_cn) == "",
                ),
            )
            .distinct()
            .order_by(model.shop_id, model.category_name)
            .limit(limit)
        )
        if shop_id is not None:
            category_query = category_query.where(model.shop_id == shop_id)
        categories = list((await db.execute(category_query)).all())

        translated_categories = 0
        for row in categories:
            translated = await translate_dwd_value_to_chinese(row.source)
            if not translated:
                continue
            await db.execute(
                update(model)
                .where(
                    model.shop_id == row.shop_id,
                    model.category_name == row.source,
                    or_(
                        model.category_name_cn.is_(None),
                        func.trim(model.category_name_cn) == "",
                    ),
                )
                .values(category_name_cn=translated)
            )
            translated_categories += 1

        await db.commit()
        return {
            "product_candidates": len(products),
            "translated_products": translated_products,
            "category_candidates": len(categories),
            "translated_categories": translated_categories,
        }

    async def translate_all_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
        max_batches: int = 10,
    ) -> dict[str, int | bool]:
        """Drain bounded product/category batches and report stalled APIs."""
        totals = {
            "batches": 0,
            "product_candidates": 0,
            "translated_products": 0,
            "category_candidates": 0,
            "translated_categories": 0,
            "stalled": False,
        }
        for _ in range(max(1, max_batches)):
            result = await self.translate_missing(
                db, shop_id=shop_id, batch_size=batch_size
            )
            candidates = result["product_candidates"] + result["category_candidates"]
            translated = result["translated_products"] + result["translated_categories"]
            if candidates == 0:
                break
            totals["batches"] += 1
            for key in (
                "product_candidates",
                "translated_products",
                "category_candidates",
                "translated_categories",
            ):
                totals[key] += result[key]
            if translated == 0:
                totals["stalled"] = True
                break
        return totals


ozon_advert_efficiency_translation_service = OzonAdvertEfficiencyTranslationService()
