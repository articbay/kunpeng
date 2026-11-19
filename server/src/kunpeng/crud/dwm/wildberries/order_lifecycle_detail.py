"""Build the Wildberries order-item lifecycle DWM."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.constants.wb_order_status import (WB_ORDER_STATUS_CN,
                                               WB_SUPPLIER_STATUS_CN)


def _canonical_status_sql(
    source_column: str,
    translation_column: str,
    translations: dict[str, str],
) -> str:
    """Build a SQL CASE that overrides known codes and preserves unknown text."""
    clauses = "\n".join(
        f"WHEN '{status}' THEN '{translation.replace(chr(39), chr(39) * 2)}'"
        for status, translation in translations.items()
    )
    return (
        f"CASE LOWER(TRIM({source_column}))\n"
        f"{clauses}\n"
        f"ELSE {translation_column}\n"
        "END"
    )


_SUPPLIER_STATUS_CN_SQL = _canonical_status_sql(
    "source.supplier_status",
    "source.supplier_status_cn",
    WB_SUPPLIER_STATUS_CN,
)
_WB_STATUS_CN_SQL = _canonical_status_sql(
    "source.wb_status",
    "source.wb_status_cn",
    WB_ORDER_STATUS_CN,
)


class CRUDDWMWBOrderLifecycleDetail:
    """Refresh WB lifecycle rows using only deterministic business-key links."""

    _source_date_bounds_statement = text(
        """
        SELECT MIN(order_date) AS date_from, MAX(order_date) AS date_to
        FROM (
            SELECT DATE(order_date) AS order_date
            FROM dwd_wb_order_statistics_detail
            WHERE order_date IS NOT NULL AND srid IS NOT NULL AND srid <> ''
            UNION ALL
            SELECT DATE(created_at)
            FROM ods_wb_marketplace_orders
            WHERE created_at IS NOT NULL AND rid IS NOT NULL AND rid <> ''
        ) AS source_dates
        """
    )

    _target_date_bounds_statement = text(
        """
        SELECT MIN(DATE(order_at)) AS date_from, MAX(DATE(order_at)) AS date_to
        FROM dwm_wb_order_lifecycle_detail
        """
    )

    _return_order_dates_statement = text(
        """
        SELECT DISTINCT order_dt
        FROM dwd_wb_return_detail
        WHERE order_dt IS NOT NULL
        ORDER BY order_dt
        """
    )

    _refresh_statement = text(
        f"""
        INSERT INTO dwm_wb_order_lifecycle_detail (
            shop_id, srid, order_id, order_uid, supply_id, sticker_id, g_number,
            nm_id, supplier_article, barcode, product_title, product_title_cn,
            subject_name, subject_name_cn, tech_size, tech_size_cn,
            delivery_type, warehouse_name, warehouse_name_cn,
            country_name, country_name_cn, region_name, region_name_cn,
            total_price, price_with_disc, finished_price,
            converted_price, currency_code,
            order_at, last_change_at, cancelled_at,
            supplier_status, supplier_status_cn, wb_status, wb_status_cn,
            lifecycle_stage, lifecycle_stage_cn,
            is_cancelled, is_sold, is_terminal,
            supply_name, supply_is_done, supply_created_at, supply_scan_at,
            supply_closed_at, supply_rejected_at,
            sale_at, sale_last_change_at, sale_id, sale_event_type,
            finance_row_cnt, finance_sale_row_cnt, finance_first_sale_at,
            return_cnt, latest_return_srid, latest_return_order_id,
            latest_return_status, latest_return_status_cn,
            latest_return_type, latest_return_type_cn,
            latest_return_reason, latest_return_reason_cn,
            return_ready_at, return_completed_at, return_expired_at,
            return_link_method, has_return_identity_conflict,
            has_statistics_order_data, has_marketplace_order_data,
            has_supply_data, has_sale_data, has_finance_data, has_return_data
        )
        WITH
        marketplace_ranked AS (
            SELECT source.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY source.shop_id, source.rid
                       ORDER BY COALESCE(
                           source.update_time, source.create_time, source.created_at
                       ) DESC, source.id DESC
                   ) AS row_num
            FROM ods_wb_marketplace_orders AS source
            WHERE source.rid IS NOT NULL AND source.rid <> ''
        ),
        marketplace AS (
            SELECT * FROM marketplace_ranked WHERE row_num = 1
        ),
        order_keys AS (
            SELECT source.shop_id, source.srid,
                   MIN(source.order_at) AS order_at,
                   MAX(source.has_statistics) AS has_statistics,
                   MAX(source.has_marketplace) AS has_marketplace
            FROM (
                SELECT stats.shop_id, stats.srid, stats.order_date AS order_at,
                       1 AS has_statistics, 0 AS has_marketplace
                FROM dwd_wb_order_statistics_detail AS stats
                WHERE DATE(stats.order_date) BETWEEN :date_from AND :date_to
                  AND stats.srid IS NOT NULL AND stats.srid <> ''
                  AND (:shop_id IS NULL OR stats.shop_id = :shop_id)
                UNION ALL
                SELECT marketplace.shop_id, marketplace.rid,
                       marketplace.created_at, 0, 1
                FROM marketplace
                WHERE DATE(marketplace.created_at) BETWEEN :date_from AND :date_to
                  AND (:shop_id IS NULL OR marketplace.shop_id = :shop_id)
            ) AS source
            GROUP BY source.shop_id, source.srid
        ),
        all_order_keys AS (
            SELECT shop_id, srid
            FROM dwd_wb_order_statistics_detail
            WHERE srid IS NOT NULL AND srid <> ''
            UNION
            SELECT shop_id, rid FROM marketplace
        ),
        finance AS (
            SELECT shop_id, srid,
                   COUNT(*) AS finance_row_cnt,
                   SUM(CASE
                       WHEN COALESCE(quantity, 0) > 0
                        AND COALESCE(retail_amount, 0) > 0
                       THEN 1 ELSE 0 END) AS finance_sale_row_cnt,
                   MIN(CASE
                       WHEN COALESCE(quantity, 0) > 0
                        AND COALESCE(retail_amount, 0) > 0
                       THEN sale_dt END) AS finance_first_sale_at,
                   COUNT(DISTINCT order_id) AS order_id_count,
                   MIN(order_id) AS order_id
            FROM dwd_wb_sales_report_detail
            WHERE srid IS NOT NULL AND srid <> ''
            GROUP BY shop_id, srid
        ),
        finance_order_bridge AS (
            SELECT shop_id, order_id,
                   COUNT(DISTINCT srid) AS srid_count,
                   MIN(srid) AS srid
            FROM dwd_wb_sales_report_detail
            WHERE order_id IS NOT NULL AND srid IS NOT NULL AND srid <> ''
            GROUP BY shop_id, order_id
        ),
        return_candidates AS (
            SELECT returns.*,
                   direct.srid AS direct_srid,
                   marketplace_by_order.rid AS marketplace_srid,
                   bridge.srid AS finance_srid,
                   bridge.srid_count AS finance_srid_count,
                   CASE
                       WHEN bridge.srid_count > 1 THEN 1
                       WHEN direct.srid IS NOT NULL
                        AND marketplace_by_order.rid IS NOT NULL
                        AND direct.srid <> marketplace_by_order.rid THEN 1
                       WHEN direct.srid IS NOT NULL
                        AND bridge.srid IS NOT NULL
                        AND direct.srid <> bridge.srid THEN 1
                       WHEN marketplace_by_order.rid IS NOT NULL
                        AND bridge.srid IS NOT NULL
                        AND marketplace_by_order.rid <> bridge.srid THEN 1
                       ELSE 0
                   END AS has_identity_conflict
            FROM dwd_wb_return_detail AS returns
            LEFT JOIN all_order_keys AS direct
              ON direct.shop_id = returns.shop_id AND direct.srid = returns.srid
            LEFT JOIN marketplace AS marketplace_by_order
              ON marketplace_by_order.shop_id = returns.shop_id
             AND marketplace_by_order.order_id = returns.order_id
            LEFT JOIN finance_order_bridge AS bridge
              ON bridge.shop_id = returns.shop_id
             AND bridge.order_id = returns.order_id
        ),
        linked_returns AS (
            SELECT candidates.*,
                   CASE
                       WHEN candidates.has_identity_conflict = 1 THEN NULL
                       ELSE COALESCE(
                           candidates.direct_srid,
                           candidates.marketplace_srid,
                           CASE WHEN candidates.finance_srid_count = 1
                                THEN candidates.finance_srid END
                       )
                   END AS canonical_srid,
                   CASE
                       WHEN candidates.has_identity_conflict = 1 THEN NULL
                       WHEN candidates.direct_srid IS NOT NULL THEN 'direct_srid'
                       WHEN candidates.marketplace_srid IS NOT NULL
                        AND candidates.finance_srid IS NOT NULL
                           THEN 'order_id_cross_checked'
                       WHEN candidates.marketplace_srid IS NOT NULL
                           THEN 'marketplace_order_id'
                       WHEN candidates.finance_srid_count = 1
                           THEN 'finance_order_id'
                   END AS link_method
            FROM return_candidates AS candidates
        ),
        linked_return_ranked AS (
            SELECT linked.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY linked.shop_id, linked.canonical_srid
                       ORDER BY COALESCE(
                           linked.completed_dt, linked.ready_to_return_dt,
                           linked.expired_dt, CAST(linked.order_dt AS DATETIME)
                       ) DESC, linked.srid DESC
                   ) AS row_num
            FROM linked_returns AS linked
            WHERE linked.canonical_srid IS NOT NULL
        ),
        return_summary AS (
            SELECT shop_id, canonical_srid, COUNT(*) AS return_cnt,
                   MAX(ready_to_return_dt) AS return_ready_at,
                   MAX(completed_dt) AS return_completed_at,
                   MAX(expired_dt) AS return_expired_at
            FROM linked_returns
            WHERE canonical_srid IS NOT NULL
            GROUP BY shop_id, canonical_srid
        ),
        latest_return AS (
            SELECT * FROM linked_return_ranked WHERE row_num = 1
        ),
        source_rows AS (
            SELECT keys_.shop_id, keys_.srid,
                   COALESCE(
                       marketplace.order_id,
                       CASE WHEN finance.order_id_count = 1
                            THEN finance.order_id END
                   ) AS order_id,
                   marketplace.order_uid, marketplace.supply_id,
                   COALESCE(stats.sticker_id, order_detail.sticker_id, sale.sticker)
                       AS sticker_id,
                   COALESCE(stats.g_number, sale.g_number) AS g_number,
                   COALESCE(stats.nm_id, marketplace.nm_id, order_detail.nm_id)
                       AS nm_id,
                   COALESCE(stats.supplier_article, marketplace.article,
                            order_detail.supplier_article, sale.supplier_article)
                       AS supplier_article,
                   COALESCE(stats.barcode_hand, stats.barcode_ori,
                            order_detail.barcode_hand, order_detail.barcode_ori,
                            sale.barcode) AS barcode,
                   order_detail.title AS product_title,
                   order_detail.title_cn AS product_title_cn,
                   COALESCE(stats.subject_name, sale.subject) AS subject_name,
                   stats.subject_name_cn,
                   COALESCE(stats.tech_size, order_detail.tech_size, sale.tech_size)
                       AS tech_size,
                   COALESCE(stats.tech_size_cn, order_detail.tech_size_cn)
                       AS tech_size_cn,
                   COALESCE(marketplace.delivery_type, order_detail.delivery_type)
                       AS delivery_type,
                   COALESCE(stats.warehouse_name, order_detail.warehouse_name,
                            sale.warehouse_name) AS warehouse_name,
                   COALESCE(stats.warehouse_name_cn, order_detail.warehouse_name_cn)
                       AS warehouse_name_cn,
                   COALESCE(stats.country_name, sale.country_name) AS country_name,
                   stats.country_name_cn,
                   COALESCE(stats.region_name, sale.region_name) AS region_name,
                   stats.region_name_cn,
                   COALESCE(stats.total_price, sale.total_price) AS total_price,
                   COALESCE(stats.price_with_disc, sale.price_with_disc)
                       AS price_with_disc,
                   COALESCE(stats.finished_price, sale.finished_price)
                       AS finished_price,
                   COALESCE(marketplace.converted_price,
                            order_detail.converted_price) AS converted_price,
                   COALESCE(marketplace.currency_code, order_detail.currency_code)
                       AS currency_code,
                   COALESCE(stats.order_date, marketplace.created_at, keys_.order_at)
                       AS order_at,
                   COALESCE(stats.last_change_date, sale.last_change_date)
                       AS last_change_at,
                   CASE WHEN stats.is_cancel = 1
                          AND stats.cancel_date > '1000-01-01'
                        THEN stats.cancel_date END AS cancelled_at,
                   COALESCE(marketplace.supplier_status,
                            order_detail.supplier_status) AS supplier_status,
                   order_detail.supplier_status_cn,
                   COALESCE(marketplace.wb_status, order_detail.wb_status)
                       AS wb_status,
                   order_detail.wb_status_cn,
                   supplies.name AS supply_name,
                   supplies.is_done AS supply_is_done,
                   supplies.created_at AS supply_created_at,
                   supplies.scan_at AS supply_scan_at,
                   supplies.closed_at AS supply_closed_at,
                   supplies.rejected_at AS supply_rejected_at,
                   sale.date AS sale_at,
                   sale.last_change_date AS sale_last_change_at,
                   COALESCE(sale.sale_id,
                            JSON_UNQUOTE(JSON_EXTRACT(sale.row_data, '$.saleID')))
                       AS sale_id,
                   COALESCE(finance.finance_row_cnt, 0) AS finance_row_cnt,
                   COALESCE(finance.finance_sale_row_cnt, 0)
                       AS finance_sale_row_cnt,
                   finance.finance_first_sale_at,
                   COALESCE(return_summary.return_cnt, 0) AS return_cnt,
                   latest_return.srid AS latest_return_srid,
                   latest_return.order_id AS latest_return_order_id,
                   latest_return.status AS latest_return_status,
                   latest_return.status_cn AS latest_return_status_cn,
                   latest_return.return_type AS latest_return_type,
                   latest_return.return_type_cn AS latest_return_type_cn,
                   latest_return.reason AS latest_return_reason,
                   latest_return.reason_cn AS latest_return_reason_cn,
                   return_summary.return_ready_at,
                   return_summary.return_completed_at,
                   return_summary.return_expired_at,
                   latest_return.link_method AS return_link_method,
                   keys_.has_statistics, keys_.has_marketplace,
                   CASE WHEN supplies.supply_id IS NULL THEN 0 ELSE 1 END
                       AS has_supply,
                   CASE WHEN sale.srid IS NULL THEN 0 ELSE 1 END AS has_sale,
                   CASE WHEN finance.srid IS NULL THEN 0 ELSE 1 END AS has_finance
            FROM order_keys AS keys_
            LEFT JOIN dwd_wb_order_statistics_detail AS stats
              ON stats.shop_id = keys_.shop_id AND stats.srid = keys_.srid
            LEFT JOIN marketplace
              ON marketplace.shop_id = keys_.shop_id
             AND marketplace.rid = keys_.srid
            LEFT JOIN dwd_wb_order_detail AS order_detail
              ON order_detail.shop_id = marketplace.shop_id
             AND order_detail.order_id = marketplace.order_id
            LEFT JOIN ods_wb_order_fbs_supplies AS supplies
              ON supplies.shop_id = marketplace.shop_id
             AND supplies.supply_id = marketplace.supply_id
            LEFT JOIN ods_wb_supplier_sales AS sale
              ON sale.shop_id = keys_.shop_id AND sale.srid = keys_.srid
            LEFT JOIN finance
              ON finance.shop_id = keys_.shop_id AND finance.srid = keys_.srid
            LEFT JOIN return_summary
              ON return_summary.shop_id = keys_.shop_id
             AND return_summary.canonical_srid = keys_.srid
            LEFT JOIN latest_return
              ON latest_return.shop_id = keys_.shop_id
             AND latest_return.canonical_srid = keys_.srid
             AND latest_return.row_num = 1
        )
        SELECT source.shop_id, source.srid, source.order_id, source.order_uid,
               source.supply_id, source.sticker_id, source.g_number,
               source.nm_id, source.supplier_article, source.barcode,
               source.product_title, source.product_title_cn,
               source.subject_name, source.subject_name_cn,
               source.tech_size, source.tech_size_cn, source.delivery_type,
               source.warehouse_name, source.warehouse_name_cn,
               source.country_name, source.country_name_cn,
               source.region_name, source.region_name_cn,
               source.total_price, source.price_with_disc, source.finished_price,
               source.converted_price, source.currency_code,
               source.order_at, source.last_change_at, source.cancelled_at,
               source.supplier_status,
               {_SUPPLIER_STATUS_CN_SQL},
               source.wb_status,
               {_WB_STATUS_CN_SQL},
               CASE
                   WHEN source.return_cnt > 0 THEN 'returned'
                   WHEN source.cancelled_at IS NOT NULL
                     OR source.supplier_status IN ('cancel', 'cancel_missed_call')
                     OR source.wb_status IN ('canceled', 'canceled_by_client',
                         'declined_by_client', 'defect',
                         'canceled_by_missed_call') THEN 'cancelled'
                   WHEN source.wb_status = 'sold'
                     OR COALESCE(source.sale_id, '') LIKE 'S%'
                     OR source.finance_sale_row_cnt > 0 THEN 'sold'
                   WHEN source.wb_status = 'ready_for_pickup'
                       THEN 'ready_for_pickup'
                   WHEN source.wb_status = 'sorted' THEN 'wb_received'
                   WHEN source.supplier_status IN ('complete', 'deliver')
                     OR source.wb_status IN ('accepted_by_carrier',
                         'sent_to_carrier', 'postponed_delivery')
                       THEN 'in_delivery'
                   WHEN source.supplier_status = 'confirm' THEN 'assembling'
                   WHEN source.supplier_status = 'new' THEN 'new'
                   ELSE 'unknown'
               END,
               CASE
                   WHEN source.return_cnt > 0 THEN '发生退货'
                   WHEN source.cancelled_at IS NOT NULL
                     OR source.supplier_status IN ('cancel', 'cancel_missed_call')
                     OR source.wb_status IN ('canceled', 'canceled_by_client',
                         'declined_by_client', 'defect',
                         'canceled_by_missed_call') THEN '已取消'
                   WHEN source.wb_status = 'sold'
                     OR COALESCE(source.sale_id, '') LIKE 'S%'
                     OR source.finance_sale_row_cnt > 0 THEN '已售出'
                   WHEN source.wb_status = 'ready_for_pickup' THEN '已到取货点'
                   WHEN source.wb_status = 'sorted' THEN 'WB已接收'
                   WHEN source.supplier_status IN ('complete', 'deliver')
                     OR source.wb_status IN ('accepted_by_carrier',
                         'sent_to_carrier', 'postponed_delivery') THEN '配送中'
                   WHEN source.supplier_status = 'confirm' THEN '组装中'
                   WHEN source.supplier_status = 'new' THEN '新订单'
                   ELSE '状态未知'
               END,
               CASE WHEN source.cancelled_at IS NOT NULL
                     OR source.supplier_status IN ('cancel', 'cancel_missed_call')
                     OR source.wb_status IN ('canceled', 'canceled_by_client',
                         'declined_by_client', 'defect',
                         'canceled_by_missed_call') THEN 1 ELSE 0 END,
               CASE WHEN source.wb_status = 'sold'
                     OR COALESCE(source.sale_id, '') LIKE 'S%'
                     OR source.finance_sale_row_cnt > 0 THEN 1 ELSE 0 END,
               CASE WHEN source.return_cnt > 0
                     OR source.cancelled_at IS NOT NULL
                     OR source.supplier_status IN ('cancel', 'cancel_missed_call')
                     OR source.wb_status IN ('sold', 'canceled',
                         'canceled_by_client', 'declined_by_client', 'defect',
                         'canceled_by_missed_call')
                     OR COALESCE(source.sale_id, '') LIKE 'S%'
                     OR source.finance_sale_row_cnt > 0 THEN 1 ELSE 0 END,
               source.supply_name, source.supply_is_done,
               source.supply_created_at, source.supply_scan_at,
               source.supply_closed_at, source.supply_rejected_at,
               source.sale_at, source.sale_last_change_at, source.sale_id,
               CASE WHEN COALESCE(source.sale_id, '') LIKE 'S%' THEN 'sale'
                    WHEN COALESCE(source.sale_id, '') LIKE 'R%' THEN 'return'
                    WHEN source.has_sale = 1 THEN 'unknown' END,
               source.finance_row_cnt, source.finance_sale_row_cnt,
               source.finance_first_sale_at, source.return_cnt,
               source.latest_return_srid, source.latest_return_order_id,
               source.latest_return_status, source.latest_return_status_cn,
               source.latest_return_type, source.latest_return_type_cn,
               source.latest_return_reason, source.latest_return_reason_cn,
               source.return_ready_at, source.return_completed_at,
               source.return_expired_at, source.return_link_method, 0,
               source.has_statistics, source.has_marketplace,
               source.has_supply, source.has_sale, source.has_finance,
               CASE WHEN source.return_cnt > 0 THEN 1 ELSE 0 END
        FROM source_rows AS source
        ON DUPLICATE KEY UPDATE
            order_id = VALUES(order_id), order_uid = VALUES(order_uid),
            supply_id = VALUES(supply_id), sticker_id = VALUES(sticker_id),
            g_number = VALUES(g_number), nm_id = VALUES(nm_id),
            supplier_article = VALUES(supplier_article), barcode = VALUES(barcode),
            product_title = VALUES(product_title),
            product_title_cn = VALUES(product_title_cn),
            subject_name = VALUES(subject_name),
            subject_name_cn = VALUES(subject_name_cn),
            tech_size = VALUES(tech_size), tech_size_cn = VALUES(tech_size_cn),
            delivery_type = VALUES(delivery_type),
            warehouse_name = VALUES(warehouse_name),
            warehouse_name_cn = VALUES(warehouse_name_cn),
            country_name = VALUES(country_name),
            country_name_cn = VALUES(country_name_cn),
            region_name = VALUES(region_name),
            region_name_cn = VALUES(region_name_cn),
            total_price = VALUES(total_price),
            price_with_disc = VALUES(price_with_disc),
            finished_price = VALUES(finished_price),
            converted_price = VALUES(converted_price),
            currency_code = VALUES(currency_code), order_at = VALUES(order_at),
            last_change_at = VALUES(last_change_at),
            cancelled_at = VALUES(cancelled_at),
            supplier_status = VALUES(supplier_status),
            supplier_status_cn = VALUES(supplier_status_cn),
            wb_status = VALUES(wb_status), wb_status_cn = VALUES(wb_status_cn),
            lifecycle_stage = VALUES(lifecycle_stage),
            lifecycle_stage_cn = VALUES(lifecycle_stage_cn),
            is_cancelled = VALUES(is_cancelled), is_sold = VALUES(is_sold),
            is_terminal = VALUES(is_terminal), supply_name = VALUES(supply_name),
            supply_is_done = VALUES(supply_is_done),
            supply_created_at = VALUES(supply_created_at),
            supply_scan_at = VALUES(supply_scan_at),
            supply_closed_at = VALUES(supply_closed_at),
            supply_rejected_at = VALUES(supply_rejected_at),
            sale_at = VALUES(sale_at),
            sale_last_change_at = VALUES(sale_last_change_at),
            sale_id = VALUES(sale_id), sale_event_type = VALUES(sale_event_type),
            finance_row_cnt = VALUES(finance_row_cnt),
            finance_sale_row_cnt = VALUES(finance_sale_row_cnt),
            finance_first_sale_at = VALUES(finance_first_sale_at),
            return_cnt = VALUES(return_cnt),
            latest_return_srid = VALUES(latest_return_srid),
            latest_return_order_id = VALUES(latest_return_order_id),
            latest_return_status = VALUES(latest_return_status),
            latest_return_status_cn = VALUES(latest_return_status_cn),
            latest_return_type = VALUES(latest_return_type),
            latest_return_type_cn = VALUES(latest_return_type_cn),
            latest_return_reason = VALUES(latest_return_reason),
            latest_return_reason_cn = VALUES(latest_return_reason_cn),
            return_ready_at = VALUES(return_ready_at),
            return_completed_at = VALUES(return_completed_at),
            return_expired_at = VALUES(return_expired_at),
            return_link_method = VALUES(return_link_method),
            has_return_identity_conflict = VALUES(has_return_identity_conflict),
            has_statistics_order_data = VALUES(has_statistics_order_data),
            has_marketplace_order_data = VALUES(has_marketplace_order_data),
            has_supply_data = VALUES(has_supply_data),
            has_sale_data = VALUES(has_sale_data),
            has_finance_data = VALUES(has_finance_data),
            has_return_data = VALUES(has_return_data),
            update_time = CURRENT_TIMESTAMP
        """
    )

    _delete_stale_statement = text(
        """
        DELETE target FROM dwm_wb_order_lifecycle_detail AS target
        WHERE DATE(target.order_at) BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR target.shop_id = :shop_id)
          AND NOT EXISTS (
              SELECT 1 FROM dwd_wb_order_statistics_detail AS stats
              WHERE stats.shop_id = target.shop_id AND stats.srid = target.srid
                AND DATE(stats.order_date) BETWEEN :date_from AND :date_to
          )
          AND NOT EXISTS (
              SELECT 1 FROM ods_wb_marketplace_orders AS marketplace
              WHERE marketplace.shop_id = target.shop_id
                AND marketplace.rid = target.srid
                AND DATE(marketplace.created_at) BETWEEN :date_from AND :date_to
          )
        """
    )

    _return_quality_statement = text(
        """
        SELECT SUM(canonical_srid IS NULL) AS unmatched_return_rows,
               SUM(has_identity_conflict = 1) AS ambiguous_return_rows
        FROM (
            SELECT CASE
                       WHEN bridge.srid_count > 1 THEN 1
                       WHEN direct.srid IS NOT NULL AND marketplace.rid IS NOT NULL
                        AND direct.srid <> marketplace.rid THEN 1
                       WHEN direct.srid IS NOT NULL AND bridge.srid IS NOT NULL
                        AND direct.srid <> bridge.srid THEN 1
                       WHEN marketplace.rid IS NOT NULL AND bridge.srid IS NOT NULL
                        AND marketplace.rid <> bridge.srid THEN 1
                       ELSE 0
                   END AS has_identity_conflict,
                   CASE
                       WHEN bridge.srid_count > 1 THEN NULL
                       WHEN direct.srid IS NOT NULL AND marketplace.rid IS NOT NULL
                        AND direct.srid <> marketplace.rid THEN NULL
                       WHEN direct.srid IS NOT NULL AND bridge.srid IS NOT NULL
                        AND direct.srid <> bridge.srid THEN NULL
                       WHEN marketplace.rid IS NOT NULL AND bridge.srid IS NOT NULL
                        AND marketplace.rid <> bridge.srid THEN NULL
                       ELSE COALESCE(direct.srid, marketplace.rid,
                           CASE WHEN bridge.srid_count = 1 THEN bridge.srid END)
                   END AS canonical_srid
            FROM dwd_wb_return_detail AS returns
            LEFT JOIN (
                SELECT shop_id, srid FROM dwd_wb_order_statistics_detail
                UNION
                SELECT shop_id, rid FROM ods_wb_marketplace_orders
                WHERE rid IS NOT NULL AND rid <> ''
            ) AS direct
              ON direct.shop_id = returns.shop_id AND direct.srid = returns.srid
            LEFT JOIN ods_wb_marketplace_orders AS marketplace
              ON marketplace.shop_id = returns.shop_id
             AND marketplace.order_id = returns.order_id
            LEFT JOIN (
                SELECT shop_id, order_id,
                       COUNT(DISTINCT srid) AS srid_count, MIN(srid) AS srid
                FROM dwd_wb_sales_report_detail
                WHERE order_id IS NOT NULL AND srid IS NOT NULL AND srid <> ''
                GROUP BY shop_id, order_id
            ) AS bridge
              ON bridge.shop_id = returns.shop_id
             AND bridge.order_id = returns.order_id
            WHERE returns.order_dt BETWEEN :date_from AND :date_to
              AND (:shop_id IS NULL OR returns.shop_id = :shop_id)
        ) AS quality
        """
    )

    _marketplace_missing_srid_statement = text(
        """
        SELECT COUNT(*) FROM ods_wb_marketplace_orders
        WHERE DATE(created_at) BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR shop_id = :shop_id)
          AND (rid IS NULL OR rid = '')
        """
    )

    async def refresh_order_date_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        """Refresh an inclusive order cohort without committing the session."""
        if date_from > date_to:
            raise ValueError("date_from must be on or before date_to")
        if shop_id is not None and shop_id <= 0:
            raise ValueError("shop_id must be positive")
        params = {"date_from": date_from, "date_to": date_to, "shop_id": shop_id}
        refresh_result = await db.execute(self._refresh_statement, params)
        stale_result = await db.execute(self._delete_stale_statement, params)
        quality = (
            (await db.execute(self._return_quality_statement, params)).mappings().one()
        )
        missing_srid = (
            await db.execute(self._marketplace_missing_srid_statement, params)
        ).scalar_one()
        await db.flush()
        return {
            "affected_rows": max(refresh_result.rowcount or 0, 0),
            "deleted_stale_rows": max(stale_result.rowcount or 0, 0),
            "unmatched_return_rows": int(quality["unmatched_return_rows"] or 0),
            "ambiguous_return_rows": int(quality["ambiguous_return_rows"] or 0),
            "marketplace_missing_srid_rows": int(missing_srid or 0),
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

    async def get_return_order_dates(self, db: AsyncSession) -> list[date]:
        """Return original order dates affected by the available return feed."""
        return list(
            (await db.execute(self._return_order_dates_statement)).scalars().all()
        )


crud_dwm_wb_order_lifecycle_detail = CRUDDWMWBOrderLifecycleDetail()
