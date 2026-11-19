"""Permission-scoped read queries for the WB order lifecycle DWM."""

from datetime import datetime, time, timedelta
from typing import Any, Sequence

from sqlalchemy import Select, case, false, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwm import DWMWBOrderLifecycleDetail
from kunpeng.schemas.wb_order_lifecycle import WBOrderLifecycleKey


class CRUDDWMWBOrderLifecycleQuery:
    model = DWMWBOrderLifecycleDetail

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: int | None = None,
        date_from=None,
        date_to=None,
        srid: str | None = None,
        order_id: int | None = None,
        supply_id: str | None = None,
        nm_id: int | None = None,
        supplier_article: str | None = None,
        supplier_status: str | None = None,
        wb_status: str | None = None,
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
            query = query.where(model.order_at >= datetime.combine(date_from, time.min))
        if date_to is not None:
            query = query.where(
                model.order_at < datetime.combine(date_to + timedelta(days=1), time.min)
            )
        for column, value in {
            model.order_id: order_id,
            model.nm_id: nm_id,
            model.lifecycle_stage: stage,
        }.items():
            if value is not None:
                query = query.where(column == value)
        for column, value in {
            model.srid: srid,
            model.supply_id: supply_id,
            model.supplier_article: supplier_article,
            model.supplier_status: supplier_status,
            model.wb_status: wb_status,
            model.latest_return_status_cn: return_status,
            model.latest_return_reason_cn: return_reason,
        }.items():
            if value:
                query = query.where(column.contains(value.strip(), autoescape=True))
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.srid.contains(value, autoescape=True),
                    model.order_uid.contains(value, autoescape=True),
                    model.supply_id.contains(value, autoescape=True),
                    model.supplier_article.contains(value, autoescape=True),
                    model.barcode.contains(value, autoescape=True),
                    model.product_title.contains(value, autoescape=True),
                    model.product_title_cn.contains(value, autoescape=True),
                    model.latest_return_reason.contains(value, autoescape=True),
                    model.latest_return_reason_cn.contains(value, autoescape=True),
                )
            )
        anomaly_conditions = {
            "missing_current_status": (
                model.supplier_status.is_(None) & model.wb_status.is_(None)
            ),
            "return_identity_conflict": model.has_return_identity_conflict.is_(True),
            "terminal_without_time": (
                model.is_terminal.is_(True)
                & model.cancelled_at.is_(None)
                & model.sale_at.is_(None)
                & model.finance_first_sale_at.is_(None)
                & model.return_ready_at.is_(None)
                & model.return_completed_at.is_(None)
            ),
        }
        if anomaly in anomaly_conditions:
            query = query.where(anomaly_conditions[anomaly])
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        order_at = (
            self.model.order_at.asc()
            if sort_order == "asc"
            else self.model.order_at.desc()
        )
        return query.order_by(order_at, self.model.shop_id, self.model.srid)

    async def list_items(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        sort_order: str,
        **filters,
    ) -> tuple[list[DWMWBOrderLifecycleDetail], int]:
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
        self,
        db: AsyncSession,
        *,
        sort_order: str,
        **filters,
    ) -> list[DWMWBOrderLifecycleDetail]:
        query = self._ordered(
            self._apply_filters(select(self.model), **filters), sort_order
        ).limit(50000)
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBOrderLifecycleKey],
    ) -> list[DWMWBOrderLifecycleDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [(key.shop_id, key.srid) for key in keys]
        model = self.model
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.srid).in_(values),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars())

    async def get_summary(self, db: AsyncSession, **filters) -> dict[str, Any]:
        filters.pop("sort_order", None)
        base = self._apply_filters(select(self.model), **filters).subquery()
        sold_count = func.coalesce(
            func.sum(case((base.c.is_sold.is_(True), 1), else_=0)),
            0,
        )
        cancelled_count = func.coalesce(
            func.sum(case((base.c.is_cancelled.is_(True), 1), else_=0)),
            0,
        )
        returned_count = func.coalesce(
            func.sum(case((base.c.has_return_data.is_(True), 1), else_=0)),
            0,
        )
        terminal_count = func.coalesce(
            func.sum(case((base.c.is_terminal.is_(True), 1), else_=0)),
            0,
        )
        marketplace_count = func.coalesce(
            func.sum(case((base.c.has_marketplace_order_data.is_(True), 1), else_=0)),
            0,
        )
        metrics_row = (
            (
                await db.execute(
                    select(
                        func.count().label("order_count"),
                        sold_count.label("sold_count"),
                        cancelled_count.label("cancelled_count"),
                        returned_count.label("returned_count"),
                        terminal_count.label("terminal_count"),
                        marketplace_count.label("marketplace_covered_count"),
                        func.max(
                            func.coalesce(base.c.update_time, base.c.create_time)
                        ).label("updated_at"),
                    )
                )
            )
            .mappings()
            .one()
        )
        metrics = dict(metrics_row)
        updated_at = metrics.pop("updated_at")
        total = int(metrics["order_count"] or 0)
        for count_key, rate_key in (
            ("sold_count", "sold_rate"),
            ("cancelled_count", "cancelled_rate"),
            ("returned_count", "returned_rate"),
        ):
            metrics[rate_key] = float(metrics[count_key] or 0) / total if total else 0

        stage_rows = (
            (
                await db.execute(
                    select(
                        base.c.lifecycle_stage.label("stage"),
                        base.c.lifecycle_stage_cn.label("label"),
                        func.count().label("order_count"),
                    )
                    .group_by(base.c.lifecycle_stage, base.c.lifecycle_stage_cn)
                    .order_by(func.count().desc())
                )
            )
            .mappings()
            .all()
        )
        stat_date = func.date(base.c.order_at)
        trend_rows = (
            (
                await db.execute(
                    select(
                        stat_date.label("stat_date"),
                        func.count().label("order_count"),
                        sold_count.label("sold_count"),
                        cancelled_count.label("cancelled_count"),
                        returned_count.label("returned_count"),
                    )
                    .group_by(stat_date)
                    .order_by(stat_date)
                )
            )
            .mappings()
            .all()
        )
        status_rows = (
            (
                await db.execute(
                    select(
                        base.c.wb_status,
                        base.c.wb_status_cn,
                        func.count().label("order_count"),
                    )
                    .group_by(base.c.wb_status, base.c.wb_status_cn)
                    .order_by(func.count().desc())
                    .limit(10)
                )
            )
            .mappings()
            .all()
        )
        return {
            "metrics": metrics,
            "stages": [dict(row) for row in stage_rows],
            "trend": [dict(row) for row in trend_rows],
            "statuses": [dict(row) for row in status_rows],
            "updated_at": updated_at,
        }


crud_dwm_wb_order_lifecycle_query = CRUDDWMWBOrderLifecycleQuery()
