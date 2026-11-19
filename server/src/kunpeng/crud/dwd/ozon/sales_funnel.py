"""Build and query the Ozon native sales-funnel DWD table."""

from datetime import date
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon.sales_funnel import DWDOzonSalesFunnelDetail
from kunpeng.models.ods.ozon.analytics import ODSOzonAnalyticsDataDaily
from kunpeng.schemas.ozon_sales_funnel import OzonSalesFunnelKey


class CRUDDWDOzonSalesFunnelDetail:
    """Idempotently reconcile Ozon Seller Analytics SKU-day facts from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_ozon_sales_funnel_detail (
            source_ods_id, shop_id, offer_id, sku,
            product_name, category_name, stat_date,
            hits_view_search, hits_view_pdp, hits_view,
            session_view_search, session_view_pdp, session_view,
            hits_tocart_search, hits_tocart_pdp, hits_tocart,
            conv_tocart_search, conv_tocart_pdp, conv_tocart,
            ordered_units, revenue, delivered_units, cancellations, returns,
            position_category, cart_to_order_rate,
            has_core_metrics, has_outcome_metrics, source_synced_at
        )
        SELECT
            analytics.id,
            analytics.shop_id,
            products.offer_id,
            analytics.sku,
            COALESCE(NULLIF(TRIM(analytics.sku_name), ''), products.product_name),
            products.category_name,
            analytics.stat_date,
            analytics.hits_view_search,
            analytics.hits_view_pdp,
            analytics.hits_view,
            analytics.session_view_search,
            analytics.session_view_pdp,
            analytics.session_view,
            analytics.hits_tocart_search,
            analytics.hits_tocart_pdp,
            analytics.hits_tocart,
            analytics.conv_tocart_search,
            analytics.conv_tocart_pdp,
            analytics.conv_tocart,
            analytics.ordered_units,
            analytics.revenue,
            analytics.delivered_units,
            analytics.cancellations,
            analytics.returns,
            analytics.position_category,
            CASE
                WHEN COALESCE(analytics.hits_tocart, 0) = 0 THEN NULL
                ELSE ROUND(analytics.ordered_units / analytics.hits_tocart * 100, 6)
            END,
            analytics.has_core_metrics,
            analytics.has_outcome_metrics,
            analytics.synced_at
        FROM ods_ozon_analytics_data_daily AS analytics
        LEFT JOIN (
            SELECT shop_id, sku, offer_id, name AS product_name, category_name
            FROM (
                SELECT
                    shop_id, sku, offer_id, name, category_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY shop_id, sku
                        ORDER BY update_time DESC, id DESC
                    ) AS rn
                FROM ods_ozon_products
                WHERE sku IS NOT NULL
            ) AS ranked_products
            WHERE rn = 1
        ) AS products
          ON products.shop_id = analytics.shop_id
         AND products.sku = analytics.sku
        WHERE (:shop_id IS NULL OR analytics.shop_id = :shop_id)
          AND (:date_from IS NULL OR analytics.stat_date >= :date_from)
          AND (:date_to IS NULL OR analytics.stat_date <= :date_to)
        ON DUPLICATE KEY UPDATE
            source_ods_id = VALUES(source_ods_id),
            offer_id = VALUES(offer_id),
            product_name_cn = IF(
                NOT (dwd_ozon_sales_funnel_detail.product_name <=> VALUES(product_name)),
                NULL,
                dwd_ozon_sales_funnel_detail.product_name_cn
            ),
            product_name = VALUES(product_name),
            category_name_cn = IF(
                NOT (dwd_ozon_sales_funnel_detail.category_name <=> VALUES(category_name)),
                NULL,
                dwd_ozon_sales_funnel_detail.category_name_cn
            ),
            category_name = VALUES(category_name),
            hits_view_search = VALUES(hits_view_search),
            hits_view_pdp = VALUES(hits_view_pdp),
            hits_view = VALUES(hits_view),
            session_view_search = VALUES(session_view_search),
            session_view_pdp = VALUES(session_view_pdp),
            session_view = VALUES(session_view),
            hits_tocart_search = VALUES(hits_tocart_search),
            hits_tocart_pdp = VALUES(hits_tocart_pdp),
            hits_tocart = VALUES(hits_tocart),
            conv_tocart_search = VALUES(conv_tocart_search),
            conv_tocart_pdp = VALUES(conv_tocart_pdp),
            conv_tocart = VALUES(conv_tocart),
            ordered_units = VALUES(ordered_units),
            revenue = VALUES(revenue),
            delivered_units = VALUES(delivered_units),
            cancellations = VALUES(cancellations),
            returns = VALUES(returns),
            position_category = VALUES(position_category),
            cart_to_order_rate = VALUES(cart_to_order_rate),
            has_core_metrics = VALUES(has_core_metrics),
            has_outcome_metrics = VALUES(has_outcome_metrics),
            source_synced_at = VALUES(source_synced_at),
            update_time = CURRENT_TIMESTAMP
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, int]:
        query = select(func.count()).select_from(ODSOzonAnalyticsDataDaily)
        if shop_id is not None:
            query = query.where(ODSOzonAnalyticsDataDaily.shop_id == shop_id)
        if date_from is not None:
            query = query.where(ODSOzonAnalyticsDataDaily.stat_date >= date_from)
        if date_to is not None:
            query = query.where(ODSOzonAnalyticsDataDaily.stat_date <= date_to)
        source_count = int((await db.execute(query)).scalar_one())
        if source_count == 0:
            return {"source_count": 0, "affected_rows": 0}
        result = await db.execute(
            self._upsert_statement,
            {"shop_id": shop_id, "date_from": date_from, "date_to": date_to},
        )
        await db.commit()
        return {
            "source_count": source_count,
            "affected_rows": max(result.rowcount or 0, 0),
        }

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sku: Optional[int] = None,
        offer_id: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDOzonSalesFunnelDetail
        if not allowed_shop_ids:
            return query.where(false())
        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if date_from is not None:
            query = query.where(model.stat_date >= date_from)
        if date_to is not None:
            query = query.where(model.stat_date <= date_to)
        if sku is not None:
            query = query.where(model.sku == sku)
        if offer_id:
            query = query.where(
                model.offer_id.contains(offer_id.strip(), autoescape=True)
            )
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.product_name.contains(value, autoescape=True),
                    model.product_name_cn.contains(value, autoescape=True),
                    model.category_name.contains(value, autoescape=True),
                    model.category_name_cn.contains(value, autoescape=True),
                )
            )
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        model = DWDOzonSalesFunnelDetail
        date_order = (
            model.stat_date.asc() if sort_order == "asc" else model.stat_date.desc()
        )
        return query.order_by(date_order, model.shop_id.asc(), model.sku.asc())

    async def list_items(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        sort_order: str,
        **filters: Any,
    ) -> tuple[list[DWDOzonSalesFunnelDetail], int]:
        model = DWDOzonSalesFunnelDetail
        count_query = self._apply_filters(
            select(func.count()).select_from(model), **filters
        )
        total = int((await db.execute(count_query)).scalar_one())
        query = (
            self._ordered(self._apply_filters(select(model), **filters), sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await db.execute(query)).scalars().all()), total

    async def list_for_export(
        self, db: AsyncSession, *, sort_order: str, **filters: Any
    ) -> list[DWDOzonSalesFunnelDetail]:
        model = DWDOzonSalesFunnelDetail
        query = self._ordered(self._apply_filters(select(model), **filters), sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonSalesFunnelKey],
    ) -> list[DWDOzonSalesFunnelDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [(key.shop_id, key.stat_date, key.sku) for key in keys]
        model = DWDOzonSalesFunnelDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.stat_date, model.sku).in_(values),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars().all())


crud_dwd_ozon_sales_funnel_detail = CRUDDWDOzonSalesFunnelDetail()
