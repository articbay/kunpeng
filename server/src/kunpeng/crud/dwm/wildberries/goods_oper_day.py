"""Build the Wildberries SKU-day operating DWM."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDDWMWBGoodsOperDay:
    """Idempotently aggregate funnel, order, return and advertising DWD facts."""

    _refresh_statement = text(
        """
        INSERT INTO dwm_wb_goods_oper_day (
            stat_date, shop_id, nm_id,
            vendor_code, product_title, product_title_cn,
            brand_name, subject_name, subject_name_cn,
            has_funnel_data, has_order_data, has_return_data, has_ad_data,
            product_rating, feedback_rating,
            traffic_clicks, traffic_cart_qty, traffic_wishlist_qty,
            funnel_order_qty, funnel_buyout_qty, funnel_cancel_qty,
            funnel_order_amount, funnel_buyout_amount, funnel_cancel_amount,
            order_cnt, order_qty, cancelled_order_cnt, cancelled_qty,
            order_amount_sum, finished_amount_sum,
            return_cnt, return_qty, return_ready_cnt,
            return_completed_cnt, return_expired_cnt,
            ad_campaign_cnt, ad_views, ad_clicks, ad_to_cart,
            ad_order_cnt, ad_cancelled_cnt, ad_sales_qty,
            ad_spend_amount, ad_attributed_sales_amount, ad_currency,
            has_ad_currency_conflict,
            traffic_cart_rate, traffic_order_rate, traffic_buyout_rate,
            order_cancel_rate, return_rate_ordered, return_rate_buyout,
            ad_ctr, ad_cart_rate, ad_cvr, ad_cpc, ad_cpo, ad_roas, ad_drr,
            ad_click_share, estimated_organic_clicks, has_click_scope_conflict
        )
        SELECT
            keys_.stat_date,
            keys_.shop_id,
            keys_.nm_id,
            COALESCE(funnel.vendor_code, orders.vendor_code, order_dim.vendor_code),
            COALESCE(funnel.product_title, order_dim.product_title, advert.product_title),
            order_dim.product_title_cn,
            COALESCE(funnel.brand_name, returns.brand_name),
            COALESCE(funnel.subject_name, orders.subject_name, returns.subject_name),
            COALESCE(orders.subject_name_cn, returns.subject_name_cn),
            CASE WHEN funnel.stat_date IS NULL THEN 0 ELSE 1 END,
            CASE WHEN orders.stat_date IS NULL THEN 0 ELSE 1 END,
            CASE WHEN returns.stat_date IS NULL THEN 0 ELSE 1 END,
            CASE WHEN advert.stat_date IS NULL THEN 0 ELSE 1 END,
            funnel.product_rating,
            funnel.feedback_rating,
            funnel.traffic_clicks,
            funnel.traffic_cart_qty,
            funnel.traffic_wishlist_qty,
            funnel.funnel_order_qty,
            funnel.funnel_buyout_qty,
            funnel.funnel_cancel_qty,
            funnel.funnel_order_amount,
            funnel.funnel_buyout_amount,
            funnel.funnel_cancel_amount,
            COALESCE(orders.order_cnt, 0),
            COALESCE(orders.order_qty, 0),
            COALESCE(orders.cancelled_order_cnt, 0),
            COALESCE(orders.cancelled_qty, 0),
            orders.order_amount_sum,
            orders.finished_amount_sum,
            COALESCE(returns.return_cnt, 0),
            COALESCE(returns.return_qty, 0),
            COALESCE(returns.return_ready_cnt, 0),
            COALESCE(returns.return_completed_cnt, 0),
            COALESCE(returns.return_expired_cnt, 0),
            advert.ad_campaign_cnt,
            advert.ad_views,
            advert.ad_clicks,
            advert.ad_to_cart,
            advert.ad_order_cnt,
            advert.ad_cancelled_cnt,
            advert.ad_sales_qty,
            advert.ad_spend_amount,
            advert.ad_attributed_sales_amount,
            advert.ad_currency,
            COALESCE(advert.has_currency_conflict, 0),
            CASE WHEN funnel.traffic_clicks > 0
                 THEN ROUND(funnel.traffic_cart_qty / funnel.traffic_clicks, 6)
                 ELSE NULL END,
            CASE WHEN funnel.traffic_clicks > 0
                 THEN ROUND(funnel.funnel_order_qty / funnel.traffic_clicks, 6)
                 ELSE NULL END,
            CASE WHEN funnel.traffic_clicks > 0
                 THEN ROUND(funnel.funnel_buyout_qty / funnel.traffic_clicks, 6)
                 ELSE NULL END,
            CASE WHEN orders.order_qty > 0
                 THEN ROUND(orders.cancelled_qty / orders.order_qty, 6)
                 ELSE NULL END,
            CASE WHEN orders.order_qty > 0
                 THEN ROUND(COALESCE(returns.return_qty, 0) / orders.order_qty, 6)
                 ELSE NULL END,
            CASE WHEN funnel.funnel_buyout_qty > 0
                 THEN ROUND(COALESCE(returns.return_qty, 0) / funnel.funnel_buyout_qty, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_views > 0
                 THEN ROUND(advert.ad_clicks / advert.ad_views, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_clicks > 0
                 THEN ROUND(advert.ad_to_cart / advert.ad_clicks, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_clicks > 0
                 THEN ROUND(advert.ad_order_cnt / advert.ad_clicks, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_clicks > 0 AND advert.has_currency_conflict = 0
                 THEN ROUND(advert.ad_spend_amount / advert.ad_clicks, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_order_cnt > 0 AND advert.has_currency_conflict = 0
                 THEN ROUND(advert.ad_spend_amount / advert.ad_order_cnt, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_spend_amount > 0 AND advert.has_currency_conflict = 0
                 THEN ROUND(advert.ad_attributed_sales_amount / advert.ad_spend_amount, 6)
                 ELSE NULL END,
            CASE WHEN advert.ad_attributed_sales_amount > 0
                       AND advert.has_currency_conflict = 0
                 THEN ROUND(advert.ad_spend_amount / advert.ad_attributed_sales_amount, 6)
                 ELSE NULL END,
            CASE WHEN funnel.traffic_clicks > 0 AND advert.ad_clicks IS NOT NULL
                 THEN ROUND(advert.ad_clicks / funnel.traffic_clicks, 6)
                 ELSE NULL END,
            CASE WHEN funnel.traffic_clicks IS NOT NULL AND advert.ad_clicks IS NOT NULL
                 THEN GREATEST(funnel.traffic_clicks - advert.ad_clicks, 0)
                 ELSE NULL END,
            CASE WHEN funnel.traffic_clicks IS NOT NULL
                       AND advert.ad_clicks > funnel.traffic_clicks
                 THEN 1 ELSE 0 END
        FROM (
            SELECT date_from AS stat_date, shop_id, nm_id
            FROM dwd_wb_sales_funnel_detail
            WHERE date_from = date_to
              AND date_from BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            UNION
            SELECT DATE(order_date), shop_id, nm_id
            FROM dwd_wb_order_statistics_detail
            WHERE order_date >= :date_from
              AND order_date < DATE_ADD(:date_to, INTERVAL 1 DAY)
              AND nm_id IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            UNION
            SELECT order_dt, shop_id, nm_id
            FROM dwd_wb_return_detail
            WHERE order_dt BETWEEN :date_from AND :date_to
              AND nm_id IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            UNION
            SELECT stat_date, shop_id, nm_id
            FROM dwd_wb_advert_stats_daily_incr
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
        ) AS keys_
        LEFT JOIN (
            SELECT
                date_from AS stat_date,
                shop_id,
                nm_id,
                MAX(NULLIF(vendor_code, '')) AS vendor_code,
                MAX(NULLIF(title, '')) AS product_title,
                MAX(NULLIF(brand_name, '')) AS brand_name,
                MAX(NULLIF(subject_name, '')) AS subject_name,
                MAX(product_rating) AS product_rating,
                MAX(feedback_rating) AS feedback_rating,
                CASE WHEN COUNT(open_count) = 0 THEN NULL ELSE SUM(open_count) END AS traffic_clicks,
                CASE WHEN COUNT(cart_count) = 0 THEN NULL ELSE SUM(cart_count) END AS traffic_cart_qty,
                CASE WHEN COUNT(add_to_wishlist) = 0 THEN NULL ELSE SUM(add_to_wishlist) END AS traffic_wishlist_qty,
                CASE WHEN COUNT(order_count) = 0 THEN NULL ELSE SUM(order_count) END AS funnel_order_qty,
                CASE WHEN COUNT(buyout_count) = 0 THEN NULL ELSE SUM(buyout_count) END AS funnel_buyout_qty,
                CASE WHEN COUNT(cancel_count) = 0 THEN NULL ELSE SUM(cancel_count) END AS funnel_cancel_qty,
                CASE WHEN COUNT(order_sum) = 0 THEN NULL ELSE SUM(order_sum) END AS funnel_order_amount,
                CASE WHEN COUNT(buyout_sum) = 0 THEN NULL ELSE SUM(buyout_sum) END AS funnel_buyout_amount,
                CASE WHEN COUNT(cancel_sum) = 0 THEN NULL ELSE SUM(cancel_sum) END AS funnel_cancel_amount
            FROM dwd_wb_sales_funnel_detail
            WHERE date_from = date_to
              AND date_from BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY date_from, shop_id, nm_id
        ) AS funnel
          ON funnel.stat_date = keys_.stat_date
         AND funnel.shop_id = keys_.shop_id
         AND funnel.nm_id = keys_.nm_id
        LEFT JOIN (
            SELECT
                DATE(order_date) AS stat_date,
                shop_id,
                nm_id,
                MAX(NULLIF(supplier_article, '')) AS vendor_code,
                MAX(NULLIF(subject_name, '')) AS subject_name,
                MAX(NULLIF(subject_name_cn, '')) AS subject_name_cn,
                COUNT(DISTINCT srid) AS order_cnt,
                COUNT(*) AS order_qty,
                COUNT(DISTINCT CASE WHEN is_cancel = 1 THEN srid END) AS cancelled_order_cnt,
                SUM(CASE WHEN is_cancel = 1 THEN 1 ELSE 0 END) AS cancelled_qty,
                CASE WHEN COUNT(price_with_disc) = 0 THEN NULL ELSE SUM(price_with_disc) END AS order_amount_sum,
                CASE WHEN COUNT(finished_price) = 0 THEN NULL ELSE SUM(finished_price) END AS finished_amount_sum
            FROM dwd_wb_order_statistics_detail
            WHERE order_date >= :date_from
              AND order_date < DATE_ADD(:date_to, INTERVAL 1 DAY)
              AND nm_id IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY DATE(order_date), shop_id, nm_id
        ) AS orders
          ON orders.stat_date = keys_.stat_date
         AND orders.shop_id = keys_.shop_id
         AND orders.nm_id = keys_.nm_id
        LEFT JOIN (
            SELECT
                DATE(order_dt) AS stat_date,
                shop_id,
                nm_id,
                MAX(NULLIF(supplier_article, '')) AS vendor_code,
                MAX(NULLIF(title, '')) AS product_title,
                MAX(NULLIF(title_cn, '')) AS product_title_cn
            FROM dwd_wb_order_detail
            WHERE order_dt >= :date_from
              AND order_dt < DATE_ADD(:date_to, INTERVAL 1 DAY)
              AND nm_id IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY DATE(order_dt), shop_id, nm_id
        ) AS order_dim
          ON order_dim.stat_date = keys_.stat_date
         AND order_dim.shop_id = keys_.shop_id
         AND order_dim.nm_id = keys_.nm_id
        LEFT JOIN (
            SELECT
                order_dt AS stat_date,
                shop_id,
                nm_id,
                MAX(NULLIF(brand, '')) AS brand_name,
                MAX(NULLIF(subject_name, '')) AS subject_name,
                MAX(NULLIF(subject_name_cn, '')) AS subject_name_cn,
                COUNT(DISTINCT srid) AS return_cnt,
                COUNT(*) AS return_qty,
                SUM(ready_to_return_dt IS NOT NULL) AS return_ready_cnt,
                SUM(completed_dt IS NOT NULL) AS return_completed_cnt,
                SUM(expired_dt IS NOT NULL) AS return_expired_cnt
            FROM dwd_wb_return_detail
            WHERE order_dt BETWEEN :date_from AND :date_to
              AND nm_id IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY order_dt, shop_id, nm_id
        ) AS returns
          ON returns.stat_date = keys_.stat_date
         AND returns.shop_id = keys_.shop_id
         AND returns.nm_id = keys_.nm_id
        LEFT JOIN (
            SELECT
                stat_date,
                shop_id,
                nm_id,
                MAX(NULLIF(nm_name, '')) AS product_title,
                COUNT(DISTINCT advert_id) AS ad_campaign_cnt,
                CASE WHEN COUNT(views) = 0 THEN NULL ELSE SUM(views) END AS ad_views,
                CASE WHEN COUNT(clicks) = 0 THEN NULL ELSE SUM(clicks) END AS ad_clicks,
                CASE WHEN COUNT(atbs) = 0 THEN NULL ELSE SUM(atbs) END AS ad_to_cart,
                CASE WHEN COUNT(orders) = 0 THEN NULL ELSE SUM(orders) END AS ad_order_cnt,
                CASE WHEN COUNT(canceled) = 0 THEN NULL ELSE SUM(canceled) END AS ad_cancelled_cnt,
                CASE WHEN COUNT(shks) = 0 THEN NULL ELSE SUM(shks) END AS ad_sales_qty,
                CASE WHEN COUNT(DISTINCT currency) = 1 THEN SUM(sum_cost) ELSE NULL END AS ad_spend_amount,
                CASE WHEN COUNT(DISTINCT currency) = 1 THEN SUM(sum_price) ELSE NULL END AS ad_attributed_sales_amount,
                CASE WHEN COUNT(DISTINCT currency) = 1 THEN MAX(currency) ELSE NULL END AS ad_currency,
                CASE WHEN COUNT(DISTINCT currency) = 1 THEN 0 ELSE 1 END AS has_currency_conflict
            FROM dwd_wb_advert_stats_daily_incr
            WHERE stat_date BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR shop_id = :shop_id)
            GROUP BY stat_date, shop_id, nm_id
        ) AS advert
          ON advert.stat_date = keys_.stat_date
         AND advert.shop_id = keys_.shop_id
         AND advert.nm_id = keys_.nm_id
        ON DUPLICATE KEY UPDATE
            vendor_code = VALUES(vendor_code),
            product_title = VALUES(product_title),
            product_title_cn = VALUES(product_title_cn),
            brand_name = VALUES(brand_name),
            subject_name = VALUES(subject_name),
            subject_name_cn = VALUES(subject_name_cn),
            has_funnel_data = VALUES(has_funnel_data),
            has_order_data = VALUES(has_order_data),
            has_return_data = VALUES(has_return_data),
            has_ad_data = VALUES(has_ad_data),
            product_rating = VALUES(product_rating),
            feedback_rating = VALUES(feedback_rating),
            traffic_clicks = VALUES(traffic_clicks),
            traffic_cart_qty = VALUES(traffic_cart_qty),
            traffic_wishlist_qty = VALUES(traffic_wishlist_qty),
            funnel_order_qty = VALUES(funnel_order_qty),
            funnel_buyout_qty = VALUES(funnel_buyout_qty),
            funnel_cancel_qty = VALUES(funnel_cancel_qty),
            funnel_order_amount = VALUES(funnel_order_amount),
            funnel_buyout_amount = VALUES(funnel_buyout_amount),
            funnel_cancel_amount = VALUES(funnel_cancel_amount),
            order_cnt = VALUES(order_cnt),
            order_qty = VALUES(order_qty),
            cancelled_order_cnt = VALUES(cancelled_order_cnt),
            cancelled_qty = VALUES(cancelled_qty),
            order_amount_sum = VALUES(order_amount_sum),
            finished_amount_sum = VALUES(finished_amount_sum),
            return_cnt = VALUES(return_cnt),
            return_qty = VALUES(return_qty),
            return_ready_cnt = VALUES(return_ready_cnt),
            return_completed_cnt = VALUES(return_completed_cnt),
            return_expired_cnt = VALUES(return_expired_cnt),
            ad_campaign_cnt = VALUES(ad_campaign_cnt),
            ad_views = VALUES(ad_views),
            ad_clicks = VALUES(ad_clicks),
            ad_to_cart = VALUES(ad_to_cart),
            ad_order_cnt = VALUES(ad_order_cnt),
            ad_cancelled_cnt = VALUES(ad_cancelled_cnt),
            ad_sales_qty = VALUES(ad_sales_qty),
            ad_spend_amount = VALUES(ad_spend_amount),
            ad_attributed_sales_amount = VALUES(ad_attributed_sales_amount),
            ad_currency = VALUES(ad_currency),
            has_ad_currency_conflict = VALUES(has_ad_currency_conflict),
            traffic_cart_rate = VALUES(traffic_cart_rate),
            traffic_order_rate = VALUES(traffic_order_rate),
            traffic_buyout_rate = VALUES(traffic_buyout_rate),
            order_cancel_rate = VALUES(order_cancel_rate),
            return_rate_ordered = VALUES(return_rate_ordered),
            return_rate_buyout = VALUES(return_rate_buyout),
            ad_ctr = VALUES(ad_ctr),
            ad_cart_rate = VALUES(ad_cart_rate),
            ad_cvr = VALUES(ad_cvr),
            ad_cpc = VALUES(ad_cpc),
            ad_cpo = VALUES(ad_cpo),
            ad_roas = VALUES(ad_roas),
            ad_drr = VALUES(ad_drr),
            ad_click_share = VALUES(ad_click_share),
            estimated_organic_clicks = VALUES(estimated_organic_clicks),
            has_click_scope_conflict = VALUES(has_click_scope_conflict),
            update_time = CURRENT_TIMESTAMP
        """
    )

    _delete_stale_statement = text(
        """
        DELETE target
        FROM dwm_wb_goods_oper_day AS target
        WHERE target.stat_date BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR target.shop_id = :shop_id)
          AND NOT EXISTS (
              SELECT 1 FROM dwd_wb_sales_funnel_detail funnel
              WHERE funnel.date_from = target.stat_date
                AND funnel.date_to = target.stat_date
                AND funnel.shop_id = target.shop_id
                AND funnel.nm_id = target.nm_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM dwd_wb_order_statistics_detail orders
              WHERE orders.order_date >= target.stat_date
                AND orders.order_date < DATE_ADD(target.stat_date, INTERVAL 1 DAY)
                AND orders.shop_id = target.shop_id
                AND orders.nm_id = target.nm_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM dwd_wb_return_detail returns_
              WHERE returns_.order_dt = target.stat_date
                AND returns_.shop_id = target.shop_id
                AND returns_.nm_id = target.nm_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM dwd_wb_advert_stats_daily_incr advert
              WHERE advert.stat_date = target.stat_date
                AND advert.shop_id = target.shop_id
                AND advert.nm_id = target.nm_id
          )
        """
    )

    _unattributed_statement = text(
        """
        SELECT
            (SELECT COUNT(*) FROM dwd_wb_order_statistics_detail
             WHERE (order_date IS NULL OR nm_id IS NULL)
               AND (:shop_id IS NULL OR shop_id = :shop_id)) AS order_rows,
            (SELECT COUNT(*) FROM dwd_wb_return_detail
             WHERE (order_dt IS NULL OR nm_id IS NULL)
               AND (:shop_id IS NULL OR shop_id = :shop_id)) AS return_rows
        """
    )

    _source_date_bounds_statement = text(
        """
        SELECT MIN(stat_date) AS date_from, MAX(stat_date) AS date_to
        FROM (
            SELECT date_from AS stat_date
            FROM dwd_wb_sales_funnel_detail
            WHERE date_from = date_to
            UNION ALL
            SELECT DATE(order_date)
            FROM dwd_wb_order_statistics_detail
            WHERE order_date IS NOT NULL AND nm_id IS NOT NULL
            UNION ALL
            SELECT order_dt
            FROM dwd_wb_return_detail
            WHERE order_dt IS NOT NULL AND nm_id IS NOT NULL
            UNION ALL
            SELECT stat_date
            FROM dwd_wb_advert_stats_daily_incr
        ) AS source_dates
        """
    )

    _target_date_bounds_statement = text(
        """
        SELECT MIN(stat_date) AS date_from, MAX(stat_date) AS date_to
        FROM dwm_wb_goods_oper_day
        """
    )

    async def refresh_date_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        if date_from > date_to:
            raise ValueError("date_from must be on or before date_to")
        if shop_id is not None and shop_id <= 0:
            raise ValueError("shop_id must be positive")

        params = {"date_from": date_from, "date_to": date_to, "shop_id": shop_id}
        refresh_result = await db.execute(self._refresh_statement, params)
        stale_result = await db.execute(self._delete_stale_statement, params)
        unattributed = (
            (await db.execute(self._unattributed_statement, {"shop_id": shop_id}))
            .mappings()
            .one()
        )
        await db.flush()
        return {
            "affected_rows": max(refresh_result.rowcount or 0, 0),
            "deleted_stale_rows": max(stale_result.rowcount or 0, 0),
            "unattributed_order_rows": int(unattributed["order_rows"]),
            "unattributed_return_rows": int(unattributed["return_rows"]),
        }

    async def get_source_date_bounds(
        self, db: AsyncSession
    ) -> tuple[date | None, date | None]:
        row = (await db.execute(self._source_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]

    async def get_target_date_bounds(
        self, db: AsyncSession
    ) -> tuple[date | None, date | None]:
        row = (await db.execute(self._target_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]


crud_dwm_wb_goods_oper_day = CRUDDWMWBGoodsOperDay()
