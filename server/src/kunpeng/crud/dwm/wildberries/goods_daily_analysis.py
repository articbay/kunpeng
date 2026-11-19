"""Read-only queries for the Wildberries goods daily analysis DWM."""

from typing import Any, Sequence

from sqlalchemy import Select, and_, case, false, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwm import DWMWBGoodsOperDay
from kunpeng.schemas.wb_goods_daily_analysis import WBGoodsDailyKey


class CRUDDWMWBGoodsDailyAnalysis:
    model = DWMWBGoodsOperDay

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: int | None = None,
        date_from=None,
        date_to=None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        keyword: str | None = None,
        data_status: str | None = None,
        anomaly: str | None = None,
    ) -> Select[Any]:
        model = self.model
        if not allowed_shop_ids:
            return query.where(false())
        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if date_from is not None:
            query = query.where(model.stat_date >= date_from)
        if date_to is not None:
            query = query.where(model.stat_date <= date_to)
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
        if vendor_code:
            query = query.where(
                model.vendor_code.contains(vendor_code.strip(), autoescape=True)
            )
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.vendor_code.contains(value, autoescape=True),
                    model.product_title.contains(value, autoescape=True),
                    model.product_title_cn.contains(value, autoescape=True),
                    model.brand_name.contains(value, autoescape=True),
                    model.subject_name.contains(value, autoescape=True),
                    model.subject_name_cn.contains(value, autoescape=True),
                )
            )
        status_conditions = {
            "has_orders": model.has_order_data.is_(True),
            "has_returns": model.has_return_data.is_(True),
            "has_funnel": model.has_funnel_data.is_(True),
            "has_ad": model.has_ad_data.is_(True),
        }
        if data_status in status_conditions:
            query = query.where(status_conditions[data_status])
        anomaly_conditions = {
            "ad_spend_no_orders": and_(
                func.coalesce(model.ad_spend_amount, 0) > 0,
                func.coalesce(model.ad_order_cnt, 0) == 0,
            ),
            "high_return_rate": model.return_rate_ordered >= 0.2,
            "clicks_no_cart": and_(
                func.coalesce(model.traffic_clicks, 0) > 0,
                func.coalesce(model.traffic_cart_qty, 0) == 0,
            ),
            "cart_no_orders": and_(
                func.coalesce(model.traffic_cart_qty, 0) > 0,
                func.coalesce(model.funnel_order_qty, 0) == 0,
            ),
            "high_cancel_rate": model.order_cancel_rate >= 0.2,
            "click_scope_conflict": model.has_click_scope_conflict.is_(True),
            "ad_currency_conflict": model.has_ad_currency_conflict.is_(True),
        }
        if anomaly in anomaly_conditions:
            query = query.where(anomaly_conditions[anomaly])
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        date_order = (
            self.model.stat_date.asc()
            if sort_order == "asc"
            else self.model.stat_date.desc()
        )
        return query.order_by(date_order, self.model.shop_id, self.model.nm_id)

    async def list_items(
        self, db: AsyncSession, *, page: int, page_size: int, sort_order: str, **filters
    ) -> tuple[list[DWMWBGoodsOperDay], int]:
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
    ) -> list[DWMWBGoodsOperDay]:
        query = self._ordered(
            self._apply_filters(select(self.model), **filters), sort_order
        ).limit(50000)
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBGoodsDailyKey],
    ) -> list[DWMWBGoodsOperDay]:
        if not allowed_shop_ids or not keys:
            return []
        values = [(key.stat_date, key.shop_id, key.nm_id) for key in keys]
        query = select(self.model).where(
            self.model.shop_id.in_(allowed_shop_ids),
            tuple_(self.model.stat_date, self.model.shop_id, self.model.nm_id).in_(
                values
            ),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars().all())

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        ranking_metric: str = "sales_amount",
        **filters,
    ) -> dict[str, Any]:
        filters.pop("sort_order", None)
        base = self._apply_filters(select(self.model), **filters).subquery()
        metrics_query = select(
            func.coalesce(func.sum(base.c.order_amount_sum), 0).label("sales_amount"),
            func.coalesce(func.sum(base.c.order_qty), 0).label("order_qty"),
            func.coalesce(func.sum(base.c.funnel_order_qty), 0).label(
                "funnel_order_qty"
            ),
            func.max(case((base.c.has_funnel_data.is_(True), 1), else_=0)).label(
                "has_funnel_data"
            ),
            func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
            func.coalesce(func.sum(base.c.ad_spend_amount), 0).label("ad_spend"),
            func.coalesce(func.sum(base.c.ad_attributed_sales_amount), 0).label(
                "ad_attributed_sales"
            ),
            func.min(base.c.ad_currency).label("ad_currency"),
            func.max(base.c.ad_currency).label("ad_currency_max"),
            func.max(
                case((base.c.has_ad_currency_conflict.is_(True), 1), else_=0)
            ).label("row_currency_conflict"),
            func.max(func.coalesce(base.c.update_time, base.c.create_time)).label(
                "updated_at"
            ),
        )
        metrics = dict((await db.execute(metrics_query)).mappings().one())
        order_qty = int(metrics["order_qty"] or 0)
        return_qty = int(metrics["return_qty"] or 0)
        ad_spend = metrics["ad_spend"] or 0
        ad_sales = metrics["ad_attributed_sales"] or 0
        metrics["return_rate"] = return_qty / order_qty if order_qty else 0
        metrics["has_funnel_data"] = bool(metrics["has_funnel_data"])
        metrics["ad_roas"] = ad_sales / ad_spend if ad_spend else None
        metrics["ad_drr"] = ad_spend / ad_sales if ad_sales else None
        metrics["sales_currency"] = None
        metrics["has_currency_conflict"] = bool(
            metrics.pop("row_currency_conflict")
            or metrics["ad_currency"] != metrics.pop("ad_currency_max")
        )
        updated_at = metrics.pop("updated_at")

        trend_query = (
            select(
                base.c.stat_date,
                func.coalesce(func.sum(base.c.order_amount_sum), 0).label(
                    "sales_amount"
                ),
                func.coalesce(func.sum(base.c.ad_spend_amount), 0).label("ad_spend"),
                func.coalesce(func.sum(base.c.order_qty), 0).label("order_qty"),
                func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
            )
            .group_by(base.c.stat_date)
            .order_by(base.c.stat_date)
        )
        trend = [dict(row) for row in (await db.execute(trend_query)).mappings().all()]
        for row in trend:
            row["return_rate"] = (
                row["return_qty"] / row["order_qty"] if row["order_qty"] else 0
            )

        ranking_base = (
            select(
                base.c.nm_id,
                func.max(base.c.vendor_code).label("vendor_code"),
                func.max(base.c.product_title_cn).label("product_title_cn"),
                func.max(base.c.product_title).label("product_title"),
                func.coalesce(func.sum(base.c.order_amount_sum), 0).label(
                    "sales_amount"
                ),
                func.coalesce(func.sum(base.c.order_qty), 0).label("order_qty"),
                func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
                func.coalesce(func.sum(base.c.ad_spend_amount), 0).label("ad_spend"),
                func.coalesce(func.sum(base.c.ad_attributed_sales_amount), 0).label(
                    "ad_sales"
                ),
            )
            .group_by(base.c.nm_id)
            .subquery()
        )
        return_rate = case(
            (ranking_base.c.order_qty == 0, 0),
            else_=ranking_base.c.return_qty / ranking_base.c.order_qty,
        )
        roas = case(
            (ranking_base.c.ad_spend == 0, None),
            else_=ranking_base.c.ad_sales / ranking_base.c.ad_spend,
        )
        ordering = {
            "sales_amount": ranking_base.c.sales_amount,
            "order_qty": ranking_base.c.order_qty,
            "ad_spend": ranking_base.c.ad_spend,
            "ad_roas": roas,
            "return_rate": return_rate,
        }.get(ranking_metric, ranking_base.c.sales_amount)
        ranking_query = (
            select(
                ranking_base.c.nm_id,
                ranking_base.c.vendor_code,
                ranking_base.c.product_title_cn,
                ranking_base.c.product_title,
                ranking_base.c.sales_amount,
                ranking_base.c.order_qty,
                ranking_base.c.return_qty,
                return_rate.label("return_rate"),
                ranking_base.c.ad_spend,
                roas.label("ad_roas"),
            )
            .order_by(ordering.desc(), ranking_base.c.nm_id)
            .limit(10)
        )
        ranking = [
            dict(row) for row in (await db.execute(ranking_query)).mappings().all()
        ]
        return {
            "metrics": metrics,
            "trend": trend,
            "ranking": ranking,
            "updated_at": updated_at,
        }

    @staticmethod
    def _period_metrics(row: dict[str, Any]) -> dict[str, Any]:
        order_qty = int(row.get("order_qty") or 0)
        return_qty = int(row.get("return_qty") or 0)
        ad_spend = row.get("ad_spend") or 0
        ad_sales = row.get("ad_attributed_sales") or 0
        return {
            "sales_amount": row.get("sales_amount") or 0,
            "order_qty": order_qty,
            "return_qty": return_qty,
            "return_rate": return_qty / order_qty if order_qty else 0,
            "ad_spend": ad_spend,
            "ad_attributed_sales": ad_sales,
            "ad_roas": ad_sales / ad_spend if ad_spend else None,
        }

    async def get_product_detail(
        self, db: AsyncSession, *, nm_id: int, **filters
    ) -> dict[str, Any] | None:
        filters.pop("sort_order", None)
        filters["nm_id"] = nm_id
        base = self._apply_filters(select(self.model), **filters).subquery()
        detail_query = select(
            func.count().label("row_count"),
            func.max(base.c.vendor_code).label("vendor_code"),
            func.max(base.c.product_title).label("product_title"),
            func.max(base.c.product_title_cn).label("product_title_cn"),
            func.max(base.c.brand_name).label("brand_name"),
            func.max(base.c.subject_name).label("subject_name"),
            func.max(base.c.subject_name_cn).label("subject_name_cn"),
            func.min(base.c.stat_date).label("period_from"),
            func.max(base.c.stat_date).label("period_to"),
            func.coalesce(func.sum(base.c.order_amount_sum), 0).label("sales_amount"),
            func.coalesce(func.sum(base.c.order_qty), 0).label("order_qty"),
            func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
            func.coalesce(func.sum(base.c.ad_spend_amount), 0).label("ad_spend"),
            func.coalesce(func.sum(base.c.ad_attributed_sales_amount), 0).label(
                "ad_attributed_sales"
            ),
        )
        detail = dict((await db.execute(detail_query)).mappings().one())
        if not detail.pop("row_count"):
            return None

        shop_query = (
            select(
                base.c.shop_id,
                func.coalesce(func.sum(base.c.order_amount_sum), 0).label(
                    "sales_amount"
                ),
                func.coalesce(func.sum(base.c.order_qty), 0).label("order_qty"),
                func.coalesce(func.sum(base.c.return_qty), 0).label("return_qty"),
                func.coalesce(func.sum(base.c.ad_spend_amount), 0).label("ad_spend"),
                func.coalesce(func.sum(base.c.ad_attributed_sales_amount), 0).label(
                    "ad_attributed_sales"
                ),
            )
            .group_by(base.c.shop_id)
            .order_by(base.c.shop_id)
        )
        shops = [dict(row) for row in (await db.execute(shop_query)).mappings().all()]
        metrics = self._period_metrics(detail)
        for shop in shops:
            shop["metrics"] = self._period_metrics(shop)
            for key in tuple(shop):
                if key not in {"shop_id", "metrics"}:
                    shop.pop(key)
        return {
            "nm_id": nm_id,
            **{
                key: detail[key]
                for key in (
                    "vendor_code",
                    "product_title",
                    "product_title_cn",
                    "brand_name",
                    "subject_name",
                    "subject_name_cn",
                    "period_from",
                    "period_to",
                )
            },
            "metrics": metrics,
            "shops": shops,
        }


crud_dwm_wb_goods_daily_analysis = CRUDDWMWBGoodsDailyAnalysis()
