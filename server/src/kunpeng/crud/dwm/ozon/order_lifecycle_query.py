"""Read-only queries for the Ozon order lifecycle DWM."""

from datetime import datetime, time, timedelta
from typing import Any, Sequence

from sqlalchemy import Select, and_, case, false, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwm import DWMOzonOrderLifecycleDetail
from kunpeng.schemas.ozon_order_lifecycle import OzonOrderLifecycleKey


class CRUDDWMOzonOrderLifecycleQuery:
    model = DWMOzonOrderLifecycleDetail

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: int | None = None,
        date_from=None,
        date_to=None,
        fulfillment_type: str | None = None,
        posting_number: str | None = None,
        order_number: str | None = None,
        sku: int | None = None,
        offer_id: str | None = None,
        status_code: str | None = None,
        substatus_code: str | None = None,
        return_status: str | None = None,
        return_reason: str | None = None,
        keyword: str | None = None,
        stage: str | None = None,
        anomaly: str | None = None,
    ) -> Select[Any]:
        model = self.model
        if not allowed_shop_ids:
            return query.where(false())
        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if date_from is not None:
            query = query.where(
                model.in_process_at >= datetime.combine(date_from, time.min)
            )
        if date_to is not None:
            query = query.where(
                model.in_process_at
                < datetime.combine(date_to + timedelta(days=1), time.min)
            )
        exact = {
            model.fulfillment_type: fulfillment_type,
            model.sku: sku,
        }
        for column, value in exact.items():
            if value is not None:
                query = query.where(column == value)
        contains = {
            model.posting_number: posting_number,
            model.order_number: order_number,
            model.offer_id: offer_id,
            model.status_code: status_code,
            model.substatus_code: substatus_code,
            model.latest_return_status_display_name_cn: return_status,
            model.latest_return_reason_name_cn: return_reason,
        }
        for column, value in contains.items():
            if value:
                query = query.where(column.contains(value.strip(), autoescape=True))
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.posting_number.contains(value, autoescape=True),
                    model.order_number.contains(value, autoescape=True),
                    model.offer_id.contains(value, autoescape=True),
                    model.product_name.contains(value, autoescape=True),
                    model.product_name_cn.contains(value, autoescape=True),
                    model.status_name_cn.contains(value, autoescape=True),
                    model.latest_return_reason_name_cn.contains(value, autoescape=True),
                )
            )
        stage_conditions = {
            "pending_shipment": and_(
                model.shipment_date.is_(None), model.cancellation_at.is_(None)
            ),
            "shipped": model.shipment_date.is_not(None),
            "transferred": model.transferred_to_delivery_at.is_not(None),
            "delivery_node": model.delivery_date.is_not(None),
            "cancelled": model.cancellation_at.is_not(None),
            "returned": model.return_cnt > 0,
        }
        if stage in stage_conditions:
            query = query.where(stage_conditions[stage])
        anomaly_conditions = {
            "promise_passed_without_delivery_node": and_(
                model.promised_delivery_at < func.now(),
                model.delivery_date.is_(None),
                model.cancellation_at.is_(None),
            ),
            "return_qty_exceeds_ordered": model.return_qty
            > func.coalesce(model.quantity, 0),
            "return_status_missing": and_(
                model.return_cnt > 0,
                model.latest_return_status_display_name_cn.is_(None),
                model.latest_return_status_sys_name.is_(None),
            ),
        }
        if anomaly in anomaly_conditions:
            query = query.where(anomaly_conditions[anomaly])
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        time_order = (
            self.model.in_process_at.asc()
            if sort_order == "asc"
            else self.model.in_process_at.desc()
        )
        return query.order_by(
            time_order,
            self.model.shop_id,
            self.model.posting_number,
            self.model.sku,
        )

    async def list_items(
        self, db: AsyncSession, *, page: int, page_size: int, sort_order: str, **filters
    ) -> tuple[list[DWMOzonOrderLifecycleDetail], int]:
        count_query = self._apply_filters(
            select(func.count()).select_from(self.model), **filters
        )
        total = int((await db.execute(count_query)).scalar_one())
        query = (
            self._ordered(
                self._apply_filters(select(self.model), **filters), sort_order
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await db.execute(query)).scalars().all()), total

    async def list_for_export(
        self, db: AsyncSession, *, sort_order: str, **filters
    ) -> list[DWMOzonOrderLifecycleDetail]:
        query = self._ordered(
            self._apply_filters(select(self.model), **filters), sort_order
        ).limit(50000)
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonOrderLifecycleKey],
    ) -> list[DWMOzonOrderLifecycleDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [
            (key.shop_id, key.fulfillment_type, key.posting_number, key.sku)
            for key in keys
        ]
        model = self.model
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(
                model.shop_id,
                model.fulfillment_type,
                model.posting_number,
                model.sku,
            ).in_(values),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars().all())

    async def get_summary(self, db: AsyncSession, **filters) -> dict[str, Any]:
        filters.pop("sort_order", None)
        model = self.model
        base = self._apply_filters(select(model), **filters).subquery()
        posting_key = func.concat_ws(
            ":", base.c.shop_id, base.c.fulfillment_type, base.c.posting_number
        )
        posting_count = func.count(func.distinct(posting_key))
        metrics_query = select(
            posting_count.label("posting_count"),
            func.count().label("item_row_count"),
            func.coalesce(func.sum(base.c.quantity), 0).label("order_qty"),
            func.count(
                func.distinct(case((base.c.shipment_date.is_not(None), posting_key)))
            ).label("shipped_posting_count"),
            func.count(
                func.distinct(case((base.c.cancellation_at.is_not(None), posting_key)))
            ).label("cancelled_posting_count"),
            func.coalesce(func.sum(case((base.c.return_cnt > 0, 1), else_=0)), 0).label(
                "returned_item_count"
            ),
            func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
            func.max(func.coalesce(base.c.update_time, base.c.create_time)).label(
                "updated_at"
            ),
        )
        metrics = dict((await db.execute(metrics_query)).mappings().one())
        updated_at = metrics.pop("updated_at")
        postings = int(metrics["posting_count"] or 0)
        item_rows = int(metrics["item_row_count"] or 0)
        metrics["shipped_rate"] = (
            metrics["shipped_posting_count"] / postings if postings else 0
        )
        metrics["cancelled_rate"] = (
            metrics["cancelled_posting_count"] / postings if postings else 0
        )
        metrics["returned_item_rate"] = (
            metrics["returned_item_count"] / item_rows if item_rows else 0
        )

        stage_specs = (
            ("in_process", "进入处理", base.c.in_process_at.is_not(None)),
            ("shipped", "已发货", base.c.shipment_date.is_not(None)),
            (
                "transferred",
                "已移交配送",
                base.c.transferred_to_delivery_at.is_not(None),
            ),
            ("delivery_node", "已记录配送节点", base.c.delivery_date.is_not(None)),
        )
        stage_query = select(
            *[
                func.count(func.distinct(case((condition, posting_key)))).label(stage)
                for stage, _, condition in stage_specs
            ]
        )
        stage_row = (await db.execute(stage_query)).mappings().one()
        stages = [
            {"stage": stage, "label": label, "posting_count": stage_row[stage]}
            for stage, label, _ in stage_specs
        ]

        stat_date = func.date(base.c.in_process_at)
        trend_query = (
            select(
                stat_date.label("stat_date"),
                posting_count.label("posting_count"),
                func.coalesce(func.sum(base.c.quantity), 0).label("order_qty"),
                func.count(
                    func.distinct(
                        case((base.c.cancellation_at.is_not(None), posting_key))
                    )
                ).label("cancelled_posting_count"),
                func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
            )
            .group_by(stat_date)
            .order_by(stat_date)
        )
        trend = [dict(row) for row in (await db.execute(trend_query)).mappings().all()]

        status_query = (
            select(
                base.c.status_code,
                base.c.status_name_cn,
                posting_count.label("posting_count"),
            )
            .group_by(base.c.status_code, base.c.status_name_cn)
            .order_by(posting_count.desc())
            .limit(10)
        )
        statuses = [
            dict(row) for row in (await db.execute(status_query)).mappings().all()
        ]
        return {
            "metrics": metrics,
            "stages": stages,
            "trend": trend,
            "statuses": statuses,
            "updated_at": updated_at,
        }


crud_dwm_ozon_order_lifecycle_query = CRUDDWMOzonOrderLifecycleQuery()
