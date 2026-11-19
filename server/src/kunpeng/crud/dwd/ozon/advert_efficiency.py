"""Build and query the Ozon advertising efficiency DWD table."""

from datetime import date
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon.advert_efficiency import DWDOzonAdvertEfficiencyDetail
from kunpeng.models.ods.ozon.adverts import ODSOzonAdvStatProductDaily
from kunpeng.schemas.ozon_advert_efficiency import OzonAdvertEfficiencyKey


class CRUDDWDOzonAdvertEfficiencyDetail:
    """Idempotently reconcile product-level advertising statistics from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_ozon_advert_efficiency_detail (
            shop_id, stat_date, sku, product_name, category_name,
            payment_type, placement, campaign_id, campaign_name,
            money_spent, drr, orders_money, orders, ctr, views, clicks, to_cart,
            to_cart_conversion_rate, cost_per_order, cost_per_click
        )
        SELECT
            stats.shop_id,
            stats.stat_date,
            stats.sku,
            COALESCE(stats.title, products.product_name) AS product_name,
            products.category_name,
            campaigns.payment_type,
            campaigns.placement,
            stats.campaign_id,
            COALESCE(daily.title, campaigns.title) AS campaign_name,
            stats.money_spent,
            CASE
                WHEN COALESCE(stats.orders_money, 0) = 0 THEN NULL
                ELSE ROUND(stats.money_spent / stats.orders_money * 100, 4)
            END AS drr,
            stats.orders_money,
            stats.orders,
            CASE
                WHEN COALESCE(stats.views, 0) = 0 THEN NULL
                ELSE ROUND(stats.clicks / stats.views * 100, 4)
            END AS ctr,
            stats.views,
            stats.clicks,
            stats.to_cart,
            CASE
                WHEN COALESCE(stats.clicks, 0) = 0 THEN NULL
                ELSE ROUND(stats.to_cart / stats.clicks * 100, 4)
            END AS to_cart_conversion_rate,
            CASE
                WHEN COALESCE(stats.orders, 0) = 0 THEN NULL
                ELSE ROUND(stats.money_spent / stats.orders, 4)
            END AS cost_per_order,
            CASE
                WHEN COALESCE(stats.clicks, 0) = 0 THEN NULL
                ELSE ROUND(stats.money_spent / stats.clicks, 4)
            END AS cost_per_click
        FROM ods_ozon_adv_stats_product_daily AS stats
        LEFT JOIN (
            SELECT shop_id, sku, name AS product_name, category_name
            FROM (
                SELECT
                    shop_id, sku, name, category_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY shop_id, sku
                        ORDER BY update_time DESC, id DESC
                    ) AS rn
                FROM ods_ozon_products
                WHERE sku IS NOT NULL
            ) AS ranked_products
            WHERE rn = 1
        ) AS products
          ON products.shop_id = stats.shop_id
         AND products.sku = stats.sku
        LEFT JOIN ods_ozon_adv_stats_daily AS daily
          ON daily.shop_id = stats.shop_id
         AND daily.campaign_id = stats.campaign_id
         AND daily.stat_date = stats.stat_date
        LEFT JOIN ods_ozon_adv_campaigns AS campaigns
          ON campaigns.shop_id = stats.shop_id
         AND campaigns.campaign_id = stats.campaign_id
        WHERE (:shop_id IS NULL OR stats.shop_id = :shop_id)
          AND (:date_from IS NULL OR stats.stat_date >= :date_from)
          AND (:date_to IS NULL OR stats.stat_date <= :date_to)
        ON DUPLICATE KEY UPDATE
            product_name_cn = IF(
                NOT (
                    dwd_ozon_advert_efficiency_detail.product_name
                    <=> VALUES(product_name)
                ),
                NULL,
                dwd_ozon_advert_efficiency_detail.product_name_cn
            ),
            product_name = VALUES(product_name),
            category_name_cn = IF(
                NOT (
                    dwd_ozon_advert_efficiency_detail.category_name
                    <=> VALUES(category_name)
                ),
                NULL,
                dwd_ozon_advert_efficiency_detail.category_name_cn
            ),
            category_name = VALUES(category_name),
            payment_type = VALUES(payment_type),
            placement = VALUES(placement),
            campaign_name = VALUES(campaign_name),
            money_spent = VALUES(money_spent),
            drr = VALUES(drr),
            orders_money = VALUES(orders_money),
            orders = VALUES(orders),
            ctr = VALUES(ctr),
            views = VALUES(views),
            clicks = VALUES(clicks),
            to_cart = VALUES(to_cart),
            to_cart_conversion_rate = VALUES(to_cart_conversion_rate),
            cost_per_order = VALUES(cost_per_order),
            cost_per_click = VALUES(cost_per_click)
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
        source_query = select(func.count()).select_from(ODSOzonAdvStatProductDaily)
        if shop_id is not None:
            source_query = source_query.where(
                ODSOzonAdvStatProductDaily.shop_id == shop_id
            )
        if date_from is not None:
            source_query = source_query.where(
                ODSOzonAdvStatProductDaily.stat_date >= date_from
            )
        if date_to is not None:
            source_query = source_query.where(
                ODSOzonAdvStatProductDaily.stat_date <= date_to
            )
        source_count = int((await db.execute(source_query)).scalar_one())
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
        campaign_id: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDOzonAdvertEfficiencyDetail
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
        if campaign_id:
            query = query.where(
                model.campaign_id.contains(campaign_id.strip(), autoescape=True)
            )
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.product_name.contains(value, autoescape=True),
                    model.product_name_cn.contains(value, autoescape=True),
                    model.category_name.contains(value, autoescape=True),
                    model.category_name_cn.contains(value, autoescape=True),
                    model.campaign_name.contains(value, autoescape=True),
                )
            )
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        model = DWDOzonAdvertEfficiencyDetail
        date_order = (
            model.stat_date.asc() if sort_order == "asc" else model.stat_date.desc()
        )
        return query.order_by(
            date_order,
            model.shop_id.asc(),
            model.campaign_id.asc(),
            model.sku.asc(),
        )

    async def list_items(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        sort_order: str,
        **filters: Any,
    ) -> tuple[list[DWDOzonAdvertEfficiencyDetail], int]:
        model = DWDOzonAdvertEfficiencyDetail
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
    ) -> list[DWDOzonAdvertEfficiencyDetail]:
        model = DWDOzonAdvertEfficiencyDetail
        query = self._ordered(self._apply_filters(select(model), **filters), sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonAdvertEfficiencyKey],
    ) -> list[DWDOzonAdvertEfficiencyDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [
            (key.shop_id, key.stat_date, key.sku, key.campaign_id) for key in keys
        ]
        model = DWDOzonAdvertEfficiencyDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.stat_date, model.sku, model.campaign_id).in_(
                values
            ),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars().all())


crud_dwd_ozon_advert_efficiency_detail = CRUDDWDOzonAdvertEfficiencyDetail()
