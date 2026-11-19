"""Read-only queries for the unified Ozon order DWD table."""

from datetime import date
from typing import Any, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon import DWDOzonOrderDetail
from kunpeng.schemas.ozon_order import OzonOrderKey


class CRUDDWDOzonOrderQuery:
    """Apply authorization-aware filters to unified Ozon order rows."""

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        fulfillment_type: Optional[str] = None,
        posting_number: Optional[str] = None,
        order_id: Optional[int] = None,
        order_number: Optional[str] = None,
        sku: Optional[int] = None,
        offer_id: Optional[str] = None,
        status_code: Optional[str] = None,
        substatus_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        delivery_region: Optional[str] = None,
        delivery_city: Optional[str] = None,
        payment_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDOzonOrderDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if date_from is not None:
            query = query.where(model.in_process_date >= date_from)
        if date_to is not None:
            query = query.where(model.in_process_date <= date_to)
        if fulfillment_type:
            query = query.where(model.fulfillment_type == fulfillment_type)
        if posting_number:
            query = query.where(
                model.posting_number.contains(posting_number.strip(), autoescape=True)
            )
        if order_id is not None:
            query = query.where(model.order_id == order_id)
        if order_number:
            query = query.where(
                model.order_number.contains(order_number.strip(), autoescape=True)
            )
        if sku is not None:
            query = query.where(model.sku == sku)
        if offer_id:
            query = query.where(
                model.offer_id.contains(offer_id.strip(), autoescape=True)
            )
        if status_code:
            value = status_code.strip()
            query = query.where(
                or_(
                    model.status_code.contains(value, autoescape=True),
                    model.status_name_cn.contains(value, autoescape=True),
                )
            )
        if substatus_code:
            query = query.where(
                model.substatus_code.contains(substatus_code.strip(), autoescape=True)
            )
        if warehouse_name:
            value = warehouse_name.strip()
            query = query.where(
                or_(
                    model.ozon_warehouse_name.contains(value, autoescape=True),
                    model.seller_warehouse_name.contains(value, autoescape=True),
                )
            )
        for column, value in (
            (model.delivery_region, delivery_region),
            (model.payment_type, payment_type),
        ):
            if value:
                query = query.where(column.contains(value.strip(), autoescape=True))
        if delivery_city:
            value = delivery_city.strip()
            query = query.where(
                or_(
                    model.delivery_city.contains(value, autoescape=True),
                    model.delivery_city_cn.contains(value, autoescape=True),
                )
            )
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.posting_number.contains(value, autoescape=True),
                    model.order_number.contains(value, autoescape=True),
                    model.product_name.contains(value, autoescape=True),
                    model.product_name_cn.contains(value, autoescape=True),
                    model.offer_id.contains(value, autoescape=True),
                    model.status_code.contains(value, autoescape=True),
                    model.substatus_code.contains(value, autoescape=True),
                    model.status_name_cn.contains(value, autoescape=True),
                    model.ozon_warehouse_name.contains(value, autoescape=True),
                    model.seller_warehouse_name.contains(value, autoescape=True),
                    model.delivery_region.contains(value, autoescape=True),
                    model.delivery_city.contains(value, autoescape=True),
                    model.delivery_city_cn.contains(value, autoescape=True),
                    model.logistics_company.contains(value, autoescape=True),
                    model.payment_type.contains(value, autoescape=True),
                    model.buyer_name.contains(value, autoescape=True),
                    model.buyer_phone.contains(value, autoescape=True),
                )
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDOzonOrderDetail
        order_time = (
            model.in_process_at.asc()
            if sort_order == "asc"
            else model.in_process_at.desc()
        )
        return query.order_by(
            order_time,
            model.shop_id.asc(),
            model.fulfillment_type.asc(),
            model.posting_number.asc(),
            model.sku.asc(),
        )

    async def count_orders(self, db: AsyncSession, **filters: Any) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(DWDOzonOrderDetail), **filters
        )
        return int((await db.execute(query)).scalar_one())

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        sort_order: str = "desc",
        **filters: Any,
    ) -> tuple[list[DWDOzonOrderDetail], int]:
        total = await self.count_orders(db, **filters)
        query = self._apply_filters(select(DWDOzonOrderDetail), **filters)
        query = (
            self._ordered_query(query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await db.execute(query)).scalars().all()), total

    async def list_orders_for_export(
        self,
        db: AsyncSession,
        *,
        sort_order: str = "desc",
        **filters: Any,
    ) -> list[DWDOzonOrderDetail]:
        query = self._apply_filters(select(DWDOzonOrderDetail), **filters)
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_orders_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonOrderKey],
    ) -> list[DWDOzonOrderDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [
            (key.shop_id, key.fulfillment_type, key.posting_number, key.sku)
            for key in keys
        ]
        model = DWDOzonOrderDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(
                model.shop_id,
                model.fulfillment_type,
                model.posting_number,
                model.sku,
            ).in_(values),
        )
        return list(
            (await db.execute(self._ordered_query(query, sort_order="desc")))
            .scalars()
            .all()
        )


crud_dwd_ozon_order_query = CRUDDWDOzonOrderQuery()
