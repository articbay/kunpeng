"""Build the Ozon goods trade, return, traffic and advertising daily DWM."""

from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDDWMOzonGoodsTradeReturnDay:
    """Idempotently aggregate the four product-day DWD sources."""

    _source_date_bounds_statement = text(
        """
        SELECT MIN(source_date) AS date_from, MAX(source_date) AS date_to
        FROM (
            SELECT in_process_date AS source_date
            FROM dwd_ozon_order_detail
            WHERE in_process_date IS NOT NULL
            UNION ALL
            SELECT DATE(order_date) AS source_date
            FROM dwd_ozon_return_detail
            WHERE order_date IS NOT NULL
            UNION ALL
            SELECT stat_date AS source_date
            FROM dwd_ozon_sales_funnel_detail
            WHERE stat_date IS NOT NULL
            UNION ALL
            SELECT stat_date AS source_date
            FROM dwd_ozon_advert_efficiency_detail
            WHERE stat_date IS NOT NULL
        ) AS source_dates
        """
    )

    _target_date_bounds_statement = text(
        """
        SELECT MIN(stat_date) AS date_from, MAX(stat_date) AS date_to
        FROM dwm_ozon_goods_trade_return_day
        """
    )

    _refresh_statement = text(
        """
        INSERT INTO dwm_ozon_goods_trade_return_day (
            stat_date,
            shop_id,
            sku,
            offer_id,
            product_name,
            product_name_cn,
            category_name,
            category_name_cn,
            order_cnt,
            order_line_cnt,
            order_qty,
            delivered_qty,
            cancelled_qty,
            sales_amount_sum,
            sales_currency,
            return_cnt,
            return_qty,
            return_amount_sum,
            return_amount_currency,
            storage_fee_sum,
            storage_fee_currency,
            utilization_fee_sum,
            utilization_fee_currency,
            commission_amount_sum,
            commission_currency,
            return_rate_ordered,
            return_rate_delivered,
            has_currency_conflict,
            has_funnel_data,
            has_traffic_metrics,
            funnel_ordered_units,
            funnel_revenue,
            traffic_views_search,
            traffic_views_pdp,
            traffic_views,
            traffic_visitors_search,
            traffic_visitors_pdp,
            traffic_visitors,
            traffic_to_cart_search,
            traffic_to_cart_pdp,
            traffic_to_cart,
            traffic_cart_rate,
            has_ad_data,
            ad_campaign_cnt,
            ad_views,
            ad_clicks,
            ad_to_cart,
            ad_spend_amount,
            ad_spend_currency,
            ad_attributed_order_cnt,
            ad_attributed_sales_amount,
            ad_ctr,
            ad_cart_rate,
            ad_cpc,
            ad_cpo,
            ad_roas,
            ad_drr
        )
        SELECT
            keys_.stat_date,
            keys_.shop_id,
            keys_.sku,
            COALESCE(ord.offer_id, funnel.offer_id, ret.offer_id),
            COALESCE(
                ord.product_name,
                funnel.product_name,
                advert.product_name,
                ret.product_name
            ),
            COALESCE(
                ord.product_name_cn,
                funnel.product_name_cn,
                advert.product_name_cn,
                ret.product_name_cn
            ),
            COALESCE(funnel.category_name, advert.category_name),
            COALESCE(funnel.category_name_cn, advert.category_name_cn),
            COALESCE(ord.order_cnt, 0),
            COALESCE(ord.order_line_cnt, 0),
            COALESCE(ord.order_qty, 0),
            COALESCE(ord.delivered_qty, 0),
            COALESCE(ord.cancelled_qty, 0),
            CASE WHEN ord.stat_date IS NULL THEN 0 ELSE ord.sales_amount_sum END,
            ord.sales_currency,
            COALESCE(ret.return_cnt, 0),
            COALESCE(ret.return_qty, 0),
            CASE WHEN ret.stat_date IS NULL THEN 0 ELSE ret.return_amount_sum END,
            ret.return_amount_currency,
            CASE WHEN ret.stat_date IS NULL THEN 0 ELSE ret.storage_fee_sum END,
            ret.storage_fee_currency,
            CASE WHEN ret.stat_date IS NULL THEN 0 ELSE ret.utilization_fee_sum END,
            ret.utilization_fee_currency,
            CASE WHEN ret.stat_date IS NULL THEN 0 ELSE ret.commission_amount_sum END,
            ret.commission_currency,
            CASE
                WHEN COALESCE(ord.order_qty, 0) > 0
                THEN ROUND(COALESCE(ret.return_qty, 0) / ord.order_qty, 6)
                ELSE 0
            END,
            CASE
                WHEN COALESCE(ord.delivered_qty, 0) > 0
                THEN ROUND(COALESCE(ret.return_qty, 0) / ord.delivered_qty, 6)
                ELSE 0
            END,
            CASE
                WHEN COALESCE(ord.currency_conflict, 0) = 1
                  OR COALESCE(ret.currency_conflict, 0) = 1
                  OR (
                      ord.sales_currency IS NOT NULL
                      AND ret.return_amount_currency IS NOT NULL
                      AND ord.sales_currency <> ret.return_amount_currency
                  )
                THEN 1
                ELSE 0
            END,
            CASE WHEN funnel.stat_date IS NULL THEN 0 ELSE 1 END,
            COALESCE(funnel.has_traffic_metrics, 0),
            funnel.funnel_ordered_units,
            funnel.funnel_revenue,
            funnel.traffic_views_search,
            funnel.traffic_views_pdp,
            funnel.traffic_views,
            funnel.traffic_visitors_search,
            funnel.traffic_visitors_pdp,
            funnel.traffic_visitors,
            funnel.traffic_to_cart_search,
            funnel.traffic_to_cart_pdp,
            funnel.traffic_to_cart,
            CASE
                WHEN funnel.traffic_visitors > 0
                THEN ROUND(funnel.traffic_to_cart / funnel.traffic_visitors, 6)
                ELSE NULL
            END,
            CASE WHEN advert.stat_date IS NULL THEN 0 ELSE 1 END,
            advert.ad_campaign_cnt,
            advert.ad_views,
            advert.ad_clicks,
            advert.ad_to_cart,
            advert.ad_spend_amount,
            CASE WHEN advert.stat_date IS NULL THEN NULL ELSE 'RUB' END,
            advert.ad_attributed_order_cnt,
            advert.ad_attributed_sales_amount,
            CASE
                WHEN advert.ad_views > 0
                THEN ROUND(advert.ad_clicks / advert.ad_views, 6)
                ELSE NULL
            END,
            CASE
                WHEN advert.ad_clicks > 0
                THEN ROUND(advert.ad_to_cart / advert.ad_clicks, 6)
                ELSE NULL
            END,
            CASE
                WHEN advert.ad_clicks > 0
                THEN ROUND(advert.ad_spend_amount / advert.ad_clicks, 4)
                ELSE NULL
            END,
            CASE
                WHEN advert.ad_attributed_order_cnt > 0
                THEN ROUND(
                    advert.ad_spend_amount / advert.ad_attributed_order_cnt,
                    4
                )
                ELSE NULL
            END,
            CASE
                WHEN advert.ad_spend_amount > 0
                THEN ROUND(
                    advert.ad_attributed_sales_amount / advert.ad_spend_amount,
                    6
                )
                ELSE NULL
            END,
            CASE
                WHEN advert.ad_attributed_sales_amount > 0
                THEN ROUND(
                    advert.ad_spend_amount / advert.ad_attributed_sales_amount,
                    6
                )
                ELSE NULL
            END
        FROM (
            SELECT
                in_process_date AS stat_date,
                shop_id,
                sku
            FROM dwd_ozon_order_detail
            WHERE in_process_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY in_process_date, shop_id, sku

            UNION

            SELECT
                DATE(order_date) AS stat_date,
                shop_id,
                nm_id AS sku
            FROM dwd_ozon_return_detail
            WHERE order_date >= :date_from
              AND order_date < DATE_ADD(:date_to, INTERVAL 1 DAY)
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY DATE(order_date), shop_id, nm_id

            UNION

            SELECT stat_date, shop_id, sku
            FROM dwd_ozon_sales_funnel_detail
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY stat_date, shop_id, sku

            UNION

            SELECT stat_date, shop_id, sku
            FROM dwd_ozon_advert_efficiency_detail
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY stat_date, shop_id, sku
        ) AS keys_
        LEFT JOIN (
            SELECT
                in_process_date AS stat_date,
                shop_id,
                sku,
                MAX(NULLIF(offer_id, '')) AS offer_id,
                MAX(NULLIF(product_name, '')) AS product_name,
                MAX(NULLIF(product_name_cn, '')) AS product_name_cn,
                COUNT(DISTINCT fulfillment_type, posting_number) AS order_cnt,
                COUNT(*) AS order_line_cnt,
                SUM(COALESCE(quantity, 0)) AS order_qty,
                SUM(
                    CASE WHEN status_code = 'delivered'
                         THEN COALESCE(quantity, 0) ELSE 0 END
                ) AS delivered_qty,
                SUM(
                    CASE WHEN status_code = 'cancelled'
                         THEN COALESCE(quantity, 0) ELSE 0 END
                ) AS cancelled_qty,
                CASE
                    WHEN SUM(seller_price IS NOT NULL) = 0 THEN 0
                    WHEN COUNT(DISTINCT NULLIF(product_currency, '')) = 1
                    THEN SUM(seller_price * COALESCE(quantity, 0))
                    ELSE NULL
                END AS sales_amount_sum,
                CASE
                    WHEN COUNT(DISTINCT NULLIF(product_currency, '')) = 1
                    THEN MAX(NULLIF(product_currency, ''))
                    ELSE NULL
                END AS sales_currency,
                CASE
                    WHEN SUM(seller_price IS NOT NULL) > 0
                     AND COUNT(DISTINCT NULLIF(product_currency, '')) <> 1
                    THEN 1 ELSE 0
                END AS currency_conflict
            FROM dwd_ozon_order_detail
            WHERE in_process_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY in_process_date, shop_id, sku
        ) AS ord
          ON ord.stat_date = keys_.stat_date
         AND ord.shop_id = keys_.shop_id
         AND ord.sku = keys_.sku
        LEFT JOIN (
            SELECT
                DATE(order_date) AS stat_date,
                shop_id,
                nm_id AS sku,
                MAX(NULLIF(offer_id, '')) AS offer_id,
                MAX(NULLIF(product_name, '')) AS product_name,
                MAX(NULLIF(product_name_cn, '')) AS product_name_cn,
                COUNT(DISTINCT return_id) AS return_cnt,
                SUM(COALESCE(quantity, 0)) AS return_qty,
                CASE
                    WHEN SUM(price_amount IS NOT NULL) = 0 THEN 0
                    WHEN COUNT(DISTINCT NULLIF(price_currency, '')) = 1
                    THEN SUM(price_amount)
                    ELSE NULL
                END AS return_amount_sum,
                CASE
                    WHEN COUNT(DISTINCT NULLIF(price_currency, '')) = 1
                    THEN MAX(NULLIF(price_currency, ''))
                    ELSE NULL
                END AS return_amount_currency,
                CASE
                    WHEN SUM(storage_fee_amount IS NOT NULL) = 0 THEN 0
                    WHEN COUNT(DISTINCT NULLIF(storage_fee_currency, '')) = 1
                    THEN SUM(storage_fee_amount)
                    ELSE NULL
                END AS storage_fee_sum,
                CASE
                    WHEN COUNT(DISTINCT NULLIF(storage_fee_currency, '')) = 1
                    THEN MAX(NULLIF(storage_fee_currency, ''))
                    ELSE NULL
                END AS storage_fee_currency,
                CASE
                    WHEN SUM(utilization_fee_amount IS NOT NULL) = 0 THEN 0
                    WHEN COUNT(DISTINCT NULLIF(utilization_fee_currency, '')) = 1
                    THEN SUM(utilization_fee_amount)
                    ELSE NULL
                END AS utilization_fee_sum,
                CASE
                    WHEN COUNT(DISTINCT NULLIF(utilization_fee_currency, '')) = 1
                    THEN MAX(NULLIF(utilization_fee_currency, ''))
                    ELSE NULL
                END AS utilization_fee_currency,
                CASE
                    WHEN SUM(commission_amount IS NOT NULL) = 0 THEN 0
                    WHEN COUNT(DISTINCT NULLIF(commission_currency, '')) = 1
                    THEN SUM(commission_amount)
                    ELSE NULL
                END AS commission_amount_sum,
                CASE
                    WHEN COUNT(DISTINCT NULLIF(commission_currency, '')) = 1
                    THEN MAX(NULLIF(commission_currency, ''))
                    ELSE NULL
                END AS commission_currency,
                CASE
                    WHEN (
                        SUM(price_amount IS NOT NULL) > 0
                        AND COUNT(DISTINCT NULLIF(price_currency, '')) <> 1
                    ) OR (
                        SUM(storage_fee_amount IS NOT NULL) > 0
                        AND COUNT(DISTINCT NULLIF(storage_fee_currency, '')) <> 1
                    ) OR (
                        SUM(utilization_fee_amount IS NOT NULL) > 0
                        AND COUNT(DISTINCT NULLIF(utilization_fee_currency, '')) <> 1
                    ) OR (
                        SUM(commission_amount IS NOT NULL) > 0
                        AND COUNT(DISTINCT NULLIF(commission_currency, '')) <> 1
                    )
                    THEN 1 ELSE 0
                END AS currency_conflict
            FROM dwd_ozon_return_detail
            WHERE order_date >= :date_from
              AND order_date < DATE_ADD(:date_to, INTERVAL 1 DAY)
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY DATE(order_date), shop_id, nm_id
        ) AS ret
          ON ret.stat_date = keys_.stat_date
         AND ret.shop_id = keys_.shop_id
         AND ret.sku = keys_.sku
        LEFT JOIN (
            SELECT
                stat_date,
                shop_id,
                sku,
                MAX(NULLIF(offer_id, '')) AS offer_id,
                MAX(NULLIF(product_name, '')) AS product_name,
                MAX(NULLIF(product_name_cn, '')) AS product_name_cn,
                MAX(NULLIF(category_name, '')) AS category_name,
                MAX(NULLIF(category_name_cn, '')) AS category_name_cn,
                CASE
                    WHEN COUNT(ordered_units) = 0 THEN NULL
                    ELSE SUM(ordered_units)
                END AS funnel_ordered_units,
                CASE
                    WHEN COUNT(revenue) = 0 THEN NULL
                    ELSE SUM(revenue)
                END AS funnel_revenue,
                CASE
                    WHEN COUNT(hits_view_search) = 0 THEN NULL
                    ELSE SUM(hits_view_search)
                END AS traffic_views_search,
                CASE
                    WHEN COUNT(hits_view_pdp) = 0 THEN NULL
                    ELSE SUM(hits_view_pdp)
                END AS traffic_views_pdp,
                CASE
                    WHEN COUNT(hits_view) = 0 THEN NULL
                    ELSE SUM(hits_view)
                END AS traffic_views,
                CASE
                    WHEN COUNT(session_view_search) = 0 THEN NULL
                    ELSE SUM(session_view_search)
                END AS traffic_visitors_search,
                CASE
                    WHEN COUNT(session_view_pdp) = 0 THEN NULL
                    ELSE SUM(session_view_pdp)
                END AS traffic_visitors_pdp,
                CASE
                    WHEN COUNT(session_view) = 0 THEN NULL
                    ELSE SUM(session_view)
                END AS traffic_visitors,
                CASE
                    WHEN COUNT(hits_tocart_search) = 0 THEN NULL
                    ELSE SUM(hits_tocart_search)
                END AS traffic_to_cart_search,
                CASE
                    WHEN COUNT(hits_tocart_pdp) = 0 THEN NULL
                    ELSE SUM(hits_tocart_pdp)
                END AS traffic_to_cart_pdp,
                CASE
                    WHEN COUNT(hits_tocart) = 0 THEN NULL
                    ELSE SUM(hits_tocart)
                END AS traffic_to_cart,
                CASE
                    WHEN COUNT(hits_view_search) > 0
                      OR COUNT(hits_view_pdp) > 0
                      OR COUNT(hits_view) > 0
                      OR COUNT(session_view_search) > 0
                      OR COUNT(session_view_pdp) > 0
                      OR COUNT(session_view) > 0
                      OR COUNT(hits_tocart_search) > 0
                      OR COUNT(hits_tocart_pdp) > 0
                      OR COUNT(hits_tocart) > 0
                    THEN 1 ELSE 0
                END AS has_traffic_metrics
            FROM dwd_ozon_sales_funnel_detail
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY stat_date, shop_id, sku
        ) AS funnel
          ON funnel.stat_date = keys_.stat_date
         AND funnel.shop_id = keys_.shop_id
         AND funnel.sku = keys_.sku
        LEFT JOIN (
            SELECT
                stat_date,
                shop_id,
                sku,
                MAX(NULLIF(product_name, '')) AS product_name,
                MAX(NULLIF(product_name_cn, '')) AS product_name_cn,
                MAX(NULLIF(category_name, '')) AS category_name,
                MAX(NULLIF(category_name_cn, '')) AS category_name_cn,
                COUNT(DISTINCT campaign_id) AS ad_campaign_cnt,
                CASE WHEN COUNT(views) = 0 THEN NULL ELSE SUM(views) END AS ad_views,
                CASE WHEN COUNT(clicks) = 0 THEN NULL ELSE SUM(clicks) END AS ad_clicks,
                CASE
                    WHEN COUNT(to_cart) = 0 THEN NULL ELSE SUM(to_cart)
                END AS ad_to_cart,
                CASE
                    WHEN COUNT(money_spent) = 0 THEN NULL ELSE SUM(money_spent)
                END AS ad_spend_amount,
                CASE
                    WHEN COUNT(orders) = 0 THEN NULL ELSE SUM(orders)
                END AS ad_attributed_order_cnt,
                CASE
                    WHEN COUNT(orders_money) = 0 THEN NULL ELSE SUM(orders_money)
                END AS ad_attributed_sales_amount
            FROM dwd_ozon_advert_efficiency_detail
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY stat_date, shop_id, sku
        ) AS advert
          ON advert.stat_date = keys_.stat_date
         AND advert.shop_id = keys_.shop_id
         AND advert.sku = keys_.sku
        ON DUPLICATE KEY UPDATE
            offer_id = VALUES(offer_id),
            product_name = VALUES(product_name),
            product_name_cn = VALUES(product_name_cn),
            category_name = VALUES(category_name),
            category_name_cn = VALUES(category_name_cn),
            order_cnt = VALUES(order_cnt),
            order_line_cnt = VALUES(order_line_cnt),
            order_qty = VALUES(order_qty),
            delivered_qty = VALUES(delivered_qty),
            cancelled_qty = VALUES(cancelled_qty),
            sales_amount_sum = VALUES(sales_amount_sum),
            sales_currency = VALUES(sales_currency),
            return_cnt = VALUES(return_cnt),
            return_qty = VALUES(return_qty),
            return_amount_sum = VALUES(return_amount_sum),
            return_amount_currency = VALUES(return_amount_currency),
            storage_fee_sum = VALUES(storage_fee_sum),
            storage_fee_currency = VALUES(storage_fee_currency),
            utilization_fee_sum = VALUES(utilization_fee_sum),
            utilization_fee_currency = VALUES(utilization_fee_currency),
            commission_amount_sum = VALUES(commission_amount_sum),
            commission_currency = VALUES(commission_currency),
            return_rate_ordered = VALUES(return_rate_ordered),
            return_rate_delivered = VALUES(return_rate_delivered),
            has_currency_conflict = VALUES(has_currency_conflict),
            has_funnel_data = VALUES(has_funnel_data),
            has_traffic_metrics = VALUES(has_traffic_metrics),
            funnel_ordered_units = VALUES(funnel_ordered_units),
            funnel_revenue = VALUES(funnel_revenue),
            traffic_views_search = VALUES(traffic_views_search),
            traffic_views_pdp = VALUES(traffic_views_pdp),
            traffic_views = VALUES(traffic_views),
            traffic_visitors_search = VALUES(traffic_visitors_search),
            traffic_visitors_pdp = VALUES(traffic_visitors_pdp),
            traffic_visitors = VALUES(traffic_visitors),
            traffic_to_cart_search = VALUES(traffic_to_cart_search),
            traffic_to_cart_pdp = VALUES(traffic_to_cart_pdp),
            traffic_to_cart = VALUES(traffic_to_cart),
            traffic_cart_rate = VALUES(traffic_cart_rate),
            has_ad_data = VALUES(has_ad_data),
            ad_campaign_cnt = VALUES(ad_campaign_cnt),
            ad_views = VALUES(ad_views),
            ad_clicks = VALUES(ad_clicks),
            ad_to_cart = VALUES(ad_to_cart),
            ad_spend_amount = VALUES(ad_spend_amount),
            ad_spend_currency = VALUES(ad_spend_currency),
            ad_attributed_order_cnt = VALUES(ad_attributed_order_cnt),
            ad_attributed_sales_amount = VALUES(ad_attributed_sales_amount),
            ad_ctr = VALUES(ad_ctr),
            ad_cart_rate = VALUES(ad_cart_rate),
            ad_cpc = VALUES(ad_cpc),
            ad_cpo = VALUES(ad_cpo),
            ad_roas = VALUES(ad_roas),
            ad_drr = VALUES(ad_drr),
            update_time = CURRENT_TIMESTAMP
        """
    )

    _delete_stale_statement = text(
        """
        DELETE target
        FROM dwm_ozon_goods_trade_return_day AS target
        WHERE target.stat_date BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR target.shop_id = :shop_id)
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_order_detail AS ord
              WHERE ord.in_process_date = target.stat_date
                AND ord.shop_id = target.shop_id
                AND ord.sku = target.sku
          )
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_return_detail AS ret
              WHERE ret.order_date >= target.stat_date
                AND ret.order_date < DATE_ADD(target.stat_date, INTERVAL 1 DAY)
                AND ret.shop_id = target.shop_id
                AND ret.nm_id = target.sku
          )
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_sales_funnel_detail AS funnel
              WHERE funnel.stat_date = target.stat_date
                AND funnel.shop_id = target.shop_id
                AND funnel.sku = target.sku
          )
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_advert_efficiency_detail AS advert
              WHERE advert.stat_date = target.stat_date
                AND advert.shop_id = target.shop_id
                AND advert.sku = target.sku
          )
        """
    )

    _unattributed_return_statement = text(
        """
        SELECT COUNT(*)
        FROM dwd_ozon_return_detail
        WHERE order_date IS NULL
          AND (:shop_id IS NULL OR shop_id = :shop_id)
        """
    )

    async def refresh_order_date_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Refresh an inclusive order-date range without committing the session."""
        if date_from > date_to:
            raise ValueError("date_from must be on or before date_to")
        if shop_id is not None and shop_id <= 0:
            raise ValueError("shop_id must be positive")

        params = {
            "date_from": date_from,
            "date_to": date_to,
            "shop_id": shop_id,
        }
        refresh_result = await db.execute(self._refresh_statement, params)
        stale_result = await db.execute(self._delete_stale_statement, params)
        unattributed_result = await db.execute(
            self._unattributed_return_statement, {"shop_id": shop_id}
        )
        await db.flush()
        return {
            "affected_rows": max(refresh_result.rowcount or 0, 0),
            "deleted_stale_rows": max(stale_result.rowcount or 0, 0),
            "unattributed_return_rows": int(unattributed_result.scalar_one()),
        }

    async def get_source_date_bounds(
        self, db: AsyncSession
    ) -> tuple[Optional[date], Optional[date]]:
        """Return the inclusive date coverage available across all DWD sources."""
        row = (await db.execute(self._source_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]

    async def get_target_date_bounds(
        self, db: AsyncSession
    ) -> tuple[Optional[date], Optional[date]]:
        """Return the inclusive date coverage already present in this DWM."""
        row = (await db.execute(self._target_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]


crud_dwm_ozon_goods_trade_return_day = CRUDDWMOzonGoodsTradeReturnDay()
