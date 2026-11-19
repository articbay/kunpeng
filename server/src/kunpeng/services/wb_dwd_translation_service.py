"""Populate Chinese companion fields for Russian marketplace DWD content."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon import DWDOzonReturnDetail
from kunpeng.models.dwd.wildberries import (
    DWDWBOrderDetail,
    DWDWBOrderStatisticsDetail,
    DWDWBReturnDetail,
    DWDWBVOCFeedbackDetail,
    DWDWBVOCQuestionDetail,
)
from kunpeng.services.translation_service import translate_dwd_value_to_chinese
from kunpeng.services.wb_order_status_translation import (
    reviewed_wb_order_status_cn,
    reviewed_wb_supplier_status_cn,
)

TranslationFields = tuple[tuple[str, str], ...]
TranslationSpec = tuple[type[Any], TranslationFields]

WB_DWD_TRANSLATION_SPECS: tuple[TranslationSpec, ...] = (
    (
        DWDWBVOCFeedbackDetail,
        (
            ("product_name", "product_name_cn"),
            ("text", "text_cn"),
            ("pros", "pros_cn"),
            ("cons", "cons_cn"),
            ("color", "color_cn"),
            ("size", "size_cn"),
            ("answer", "answer_cn"),
        ),
    ),
    (
        DWDWBVOCQuestionDetail,
        (("text", "text_cn"), ("answer", "answer_cn")),
    ),
    (
        DWDWBReturnDetail,
        (
            ("subject_name", "subject_name_cn"),
            ("status", "status_cn"),
            ("return_type", "return_type_cn"),
            ("reason", "reason_cn"),
            ("dst_office_address", "dst_office_address_cn"),
        ),
    ),
    (
        DWDWBOrderDetail,
        (
            ("title", "title_cn"),
            ("tech_size", "tech_size_cn"),
            ("color", "color_cn"),
            ("warehouse_name", "warehouse_name_cn"),
            ("wb_status", "wb_status_cn"),
            ("address", "address_cn"),
            ("supplier_status", "supplier_status_cn"),
        ),
    ),
    (
        DWDWBOrderStatisticsDetail,
        (
            ("warehouse_name", "warehouse_name_cn"),
            ("country_name", "country_name_cn"),
            ("oblast_okrug_name", "oblast_okrug_name_cn"),
            ("region_name", "region_name_cn"),
            ("category", "category_cn"),
            ("subject_name", "subject_name_cn"),
            ("tech_size", "tech_size_cn"),
        ),
    ),
    (
        DWDOzonReturnDetail,
        (
            ("category_name", "category_name_cn"),
            ("product_name", "product_name_cn"),
            ("status_display_name", "status_display_name_cn"),
            (
                "compensation_status_display_name",
                "compensation_status_display_name_cn",
            ),
            ("return_reason_name", "return_reason_name_cn"),
            ("buyer_comment", "buyer_comment_cn"),
            ("place_name", "place_name_cn"),
            ("place_address", "place_address_cn"),
            ("target_place_name", "target_place_name_cn"),
            ("target_place_address", "target_place_address_cn"),
        ),
    ),
)


class WBDWDTranslationService:
    """Populate every nonempty marketplace DWD Chinese companion field."""

    async def translate_all_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 50,
        max_batches: int = 20,
    ) -> dict[str, Any]:
        """Drain multiple batches so one scheduled run does not leave gaps."""
        totals: dict[str, dict[str, int]] = {
            model.__tablename__: {
                "scanned_rows": 0,
                "translated_values": 0,
                "failed_values": 0,
            }
            for model, _ in WB_DWD_TRANSLATION_SPECS
        }
        completed = False
        stalled = False
        batch_count = 0

        for _ in range(max(1, max_batches)):
            batch_count += 1
            result = await self.translate_missing(
                db,
                shop_id=shop_id,
                batch_size=batch_size,
            )
            scanned_values = 0
            translated_values = 0
            for table_name, table_result in result["tables"].items():
                for metric in totals[table_name]:
                    totals[table_name][metric] += table_result[metric]
                scanned_values += table_result["scanned_rows"]
                translated_values += table_result["translated_values"]

            if scanned_values == 0:
                completed = True
                break
            if translated_values == 0:
                stalled = True
                break

        return {
            "tables": totals,
            "batches": batch_count,
            "completed": completed,
            "stalled": stalled,
        }

    async def translate_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        results: dict[str, dict[str, int]] = {}
        for model, field_pairs in WB_DWD_TRANSLATION_SPECS:
            results[model.__tablename__] = await self._translate_model(
                db,
                model=model,
                field_pairs=field_pairs,
                shop_id=shop_id,
                batch_size=batch_size,
            )
        return {"tables": results}

    async def _translate_model(
        self,
        db: AsyncSession,
        *,
        model: type[Any],
        field_pairs: TranslationFields,
        shop_id: Optional[int],
        batch_size: int,
    ) -> dict[str, int]:
        missing_conditions = []
        for source_name, target_name in field_pairs:
            source = getattr(model, source_name)
            target = getattr(model, target_name)
            missing_conditions.append(
                and_(
                    source.is_not(None),
                    func.trim(source) != "",
                    or_(target.is_(None), func.trim(target) == ""),
                )
            )

        query = select(model).where(or_(*missing_conditions))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        primary_keys = list(model.__table__.primary_key.columns)
        query = query.order_by(*[column.asc() for column in primary_keys]).limit(
            max(1, min(batch_size, 500))
        )
        records = list((await db.execute(query)).scalars().all())

        translated_count = 0
        failed_count = 0
        for record in records:
            for source_name, target_name in field_pairs:
                source_value = getattr(record, source_name)
                target_value = getattr(record, target_name)
                if (target_value or "").strip() or not (source_value or "").strip():
                    continue
                translated = None
                if model is DWDWBOrderDetail and source_name == "wb_status":
                    translated = reviewed_wb_order_status_cn(source_value)
                elif model is DWDWBOrderDetail and source_name == "supplier_status":
                    translated = reviewed_wb_supplier_status_cn(source_value)
                if translated is None:
                    translated = await translate_dwd_value_to_chinese(source_value)
                if translated:
                    setattr(record, target_name, translated)
                    translated_count += 1
                else:
                    failed_count += 1

        if translated_count:
            await db.commit()
        return {
            "scanned_rows": len(records),
            "translated_values": translated_count,
            "failed_values": failed_count,
        }


wb_dwd_translation_service = WBDWDTranslationService()
