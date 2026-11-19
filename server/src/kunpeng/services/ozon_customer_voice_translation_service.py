"""Translate missing Russian customer voice fields without blocking DWD builds."""

from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon.customer_voice import DWDOzonCustomerVoiceDetail
from kunpeng.services.translation_service import translate_dwd_value_to_chinese

ORDER_STATUS_DISPLAY_CN = {
    "DELIVERED": "已送达",
    "CANCELLED": "已取消",
}
REVIEW_STATUS_DISPLAY_CN = {
    "PROCESSED": "已处理",
    "UNPROCESSED": "未处理",
}


class OzonCustomerVoiceTranslationService:
    _field_pairs = (
        ("product_name", "product_name_cn"),
        ("order_status", "order_status_cn"),
        ("review_text", "review_text_cn"),
        ("review_status", "review_status_cn"),
    )
    _fixed_mappings = {
        "order_status": ORDER_STATUS_DISPLAY_CN,
        "review_status": REVIEW_STATUS_DISPLAY_CN,
    }

    async def translate_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
    ) -> dict[str, int]:
        model = DWDOzonCustomerVoiceDetail
        missing = []
        for source, target in self._field_pairs:
            source_column = getattr(model, source)
            target_column = getattr(model, target)
            missing.append(
                and_(
                    source_column.is_not(None),
                    func.trim(source_column) != "",
                    or_(target_column.is_(None), func.trim(target_column) == ""),
                )
            )
        query = select(model).where(or_(*missing))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        rows = list((await db.execute(query.limit(batch_size))).scalars().all())

        translated_fields = 0
        for row in rows:
            for source, target in self._field_pairs:
                if (getattr(row, target) or "").strip():
                    continue
                if not (getattr(row, source) or "").strip():
                    continue
                translated = await translate_dwd_value_to_chinese(
                    getattr(row, source),
                    fixed_mapping=self._fixed_mappings.get(source),
                )
                if translated:
                    setattr(row, target, translated)
                    translated_fields += 1
        await db.commit()
        return {"processed_rows": len(rows), "translated_fields": translated_fields}

    async def translate_all_missing(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        batch_size: int = 200,
        max_batches: int = 10,
    ) -> dict[str, int | bool]:
        """Drain bounded translation batches without looping on failures."""
        total_rows = 0
        total_fields = 0
        batches = 0
        stalled = False

        for _ in range(max(1, max_batches)):
            result = await self.translate_missing(
                db, shop_id=shop_id, batch_size=batch_size
            )
            processed_rows = result["processed_rows"]
            translated_fields = result["translated_fields"]
            if processed_rows == 0:
                break

            batches += 1
            total_rows += processed_rows
            total_fields += translated_fields
            if translated_fields == 0:
                stalled = True
                break

        return {
            "batches": batches,
            "processed_rows": total_rows,
            "translated_fields": total_fields,
            "stalled": stalled,
        }


ozon_customer_voice_translation_service = OzonCustomerVoiceTranslationService()
