"""CRUD helpers for reusing Ozon delivery-city translations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon import DWDOzonOrderDetail


class CRUDDWDOzonDeliveryCityTranslation:
    """Read unique untranslated cities and apply one translation in bulk."""

    async def list_missing_cities(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        limit: int = 200,
    ) -> list[str]:
        model = DWDOzonOrderDetail
        query = (
            select(model.delivery_city)
            .where(
                model.delivery_city.is_not(None),
                func.trim(model.delivery_city) != "",
                or_(
                    model.delivery_city_cn.is_(None),
                    func.trim(model.delivery_city_cn) == "",
                ),
            )
            .group_by(model.delivery_city)
            .order_by(model.delivery_city)
            .limit(max(1, min(limit, 500)))
        )
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        return [str(value) for value in (await db.execute(query)).scalars().all()]

    async def get_existing_translation(
        self,
        db: AsyncSession,
        *,
        delivery_city: str,
    ) -> Optional[str]:
        model = DWDOzonOrderDetail
        query = (
            select(model.delivery_city_cn)
            .where(
                model.delivery_city == delivery_city,
                model.delivery_city_cn.is_not(None),
                func.trim(model.delivery_city_cn) != "",
            )
            .limit(1)
        )
        value = (await db.execute(query)).scalar_one_or_none()
        return str(value) if value else None

    async def apply_translation(
        self,
        db: AsyncSession,
        *,
        delivery_city: str,
        delivery_city_cn: str,
        shop_id: Optional[int] = None,
    ) -> int:
        model = DWDOzonOrderDetail
        statement = (
            update(model)
            .where(
                model.delivery_city == delivery_city,
                or_(
                    model.delivery_city_cn.is_(None),
                    func.trim(model.delivery_city_cn) == "",
                ),
            )
            .values(delivery_city_cn=delivery_city_cn, update_time=func.now())
        )
        if shop_id is not None:
            statement = statement.where(model.shop_id == shop_id)
        result = await db.execute(statement)
        await db.flush()
        return max(result.rowcount or 0, 0)


crud_dwd_ozon_delivery_city_translation = CRUDDWDOzonDeliveryCityTranslation()
