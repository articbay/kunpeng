"""CRUD helpers for the persistent Ozon product-name translation cache."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon import DWDOzonOrderDetail, DWDOzonProductNameTranslation

MAX_TRANSLATION_CYCLES = 3


class CRUDDWDOzonProductNameTranslation:
    """Reserve unique translations and apply cached values to all DWD rows."""

    async def list_missing_products(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[tuple[int, int, str]]:
        # Pending keys are owned by another worker. Failed keys become candidates
        # again only while they remain below the bounded retry-cycle limit.
        blocking_cache_exists = exists().where(
            DWDOzonProductNameTranslation.shop_id == DWDOzonOrderDetail.shop_id,
            DWDOzonProductNameTranslation.sku == DWDOzonOrderDetail.sku,
            or_(
                DWDOzonProductNameTranslation.product_name_cn.is_(None),
                func.trim(DWDOzonProductNameTranslation.product_name_cn) == "",
            ),
            or_(
                DWDOzonProductNameTranslation.translation_status != "failed",
                DWDOzonProductNameTranslation.attempt_count >= MAX_TRANSLATION_CYCLES,
            ),
        )
        query = (
            select(
                DWDOzonOrderDetail.shop_id,
                DWDOzonOrderDetail.sku,
                func.max(DWDOzonOrderDetail.product_name).label("product_name"),
            )
            .where(
                DWDOzonOrderDetail.product_name.is_not(None),
                func.trim(DWDOzonOrderDetail.product_name) != "",
                or_(
                    DWDOzonOrderDetail.product_name_cn.is_(None),
                    func.trim(DWDOzonOrderDetail.product_name_cn) == "",
                ),
                ~blocking_cache_exists,
            )
            .group_by(DWDOzonOrderDetail.shop_id, DWDOzonOrderDetail.sku)
            .order_by(DWDOzonOrderDetail.shop_id, DWDOzonOrderDetail.sku)
            .limit(max(1, min(limit, 500)))
        )
        if shop_id is not None:
            query = query.where(DWDOzonOrderDetail.shop_id == shop_id)
        return [
            (int(row.shop_id), int(row.sku), str(row.product_name))
            for row in (await db.execute(query)).all()
        ]

    async def get(
        self, db: AsyncSession, *, shop_id: int, sku: int
    ) -> Optional[DWDOzonProductNameTranslation]:
        return (
            await db.execute(
                select(DWDOzonProductNameTranslation).where(
                    DWDOzonProductNameTranslation.shop_id == shop_id,
                    DWDOzonProductNameTranslation.sku == sku,
                )
            )
        ).scalar_one_or_none()

    async def reserve_once(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        sku: int,
        source_product_name: str,
    ) -> bool:
        statement = (
            mysql_insert(DWDOzonProductNameTranslation)
            .values(
                shop_id=shop_id,
                sku=sku,
                source_product_name=source_product_name,
                translation_status="pending",
                attempt_count=1,
            )
            .prefix_with("IGNORE")
        )
        result = await db.execute(statement)
        await db.flush()
        return (result.rowcount or 0) == 1

    async def claim_failed_retry(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        sku: int,
    ) -> bool:
        """Atomically claim one bounded retry cycle for a failed cache key."""
        result = await db.execute(
            update(DWDOzonProductNameTranslation)
            .where(
                DWDOzonProductNameTranslation.shop_id == shop_id,
                DWDOzonProductNameTranslation.sku == sku,
                DWDOzonProductNameTranslation.translation_status == "failed",
                DWDOzonProductNameTranslation.attempt_count < MAX_TRANSLATION_CYCLES,
            )
            .values(
                translation_status="pending",
                attempt_count=DWDOzonProductNameTranslation.attempt_count + 1,
                translated_at=None,
            )
        )
        await db.flush()
        return (result.rowcount or 0) == 1

    async def complete(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        sku: int,
        status: str,
        translated_name: Optional[str],
        translation_source: Optional[str],
        translated_at: datetime,
    ) -> None:
        await db.execute(
            update(DWDOzonProductNameTranslation)
            .where(
                DWDOzonProductNameTranslation.shop_id == shop_id,
                DWDOzonProductNameTranslation.sku == sku,
                DWDOzonProductNameTranslation.translation_status == "pending",
            )
            .values(
                product_name_cn=translated_name,
                translation_status=status,
                translation_source=translation_source,
                translated_at=translated_at,
            )
        )
        await db.flush()

    async def apply_cached_name(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        sku: int,
        product_name_cn: str,
    ) -> int:
        result = await db.execute(
            update(DWDOzonOrderDetail)
            .where(
                DWDOzonOrderDetail.shop_id == shop_id,
                DWDOzonOrderDetail.sku == sku,
                or_(
                    DWDOzonOrderDetail.product_name_cn.is_(None),
                    func.trim(DWDOzonOrderDetail.product_name_cn) == "",
                ),
            )
            .values(product_name_cn=product_name_cn, update_time=func.now())
        )
        await db.flush()
        return max(result.rowcount or 0, 0)


crud_dwd_ozon_product_name_translation = CRUDDWDOzonProductNameTranslation()
