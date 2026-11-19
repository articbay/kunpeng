"""Build the Ozon order-product lifecycle detail DWM."""

from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDDWMOzonOrderLifecycleDetail:
    """Idempotently refresh order lifecycle rows for an order-date cohort."""

    _source_date_bounds_statement = text(
        """
        SELECT
            MIN(in_process_date) AS date_from,
            MAX(in_process_date) AS date_to
        FROM dwd_ozon_order_detail
        WHERE in_process_date IS NOT NULL
        """
    )

    _target_date_bounds_statement = text(
        """
        SELECT
            MIN(DATE(in_process_at)) AS date_from,
            MAX(DATE(in_process_at)) AS date_to
        FROM dwm_ozon_order_lifecycle_detail
        """
    )

    _refresh_statement = text(
        """
        INSERT INTO dwm_ozon_order_lifecycle_detail (
            shop_id,
            fulfillment_type,
            posting_number,
            sku,
            order_id,
            order_number,
            offer_id,
            product_name,
            product_name_cn,
            quantity,
            status_code,
            substatus_code,
            status_name_cn,
            in_process_at,
            shipment_date,
            transferred_to_delivery_at,
            delivery_date,
            promised_delivery_at,
            cancellation_at,
            return_cnt,
            return_qty,
            first_return_date,
            latest_return_id,
            latest_return_status_sys_name,
            latest_return_status_display_name_cn,
            latest_return_status_change_at,
            latest_return_reason_name_cn,
            last_ready_to_pickup_at,
            last_picked_up_at
        )
        SELECT
            ord.shop_id,
            ord.fulfillment_type,
            ord.posting_number,
            ord.sku,
            ord.order_id,
            ord.order_number,
            ord.offer_id,
            ord.product_name,
            ord.product_name_cn,
            ord.quantity,
            ord.status_code,
            ord.substatus_code,
            ord.status_name_cn,
            ord.in_process_at,
            ord.shipment_date,
            ord.transferred_to_delivery_at,
            ord.delivery_date,
            ord.promised_delivery_at,
            ord.cancellation_at,
            COALESCE(ret.return_cnt, 0),
            COALESCE(ret.return_qty, 0),
            ret.first_return_date,
            latest.latest_return_id,
            latest.latest_return_status_sys_name,
            latest.latest_return_status_display_name_cn,
            latest.latest_return_status_change_at,
            latest.latest_return_reason_name_cn,
            ret.last_ready_to_pickup_at,
            ret.last_picked_up_at
        FROM dwd_ozon_order_detail AS ord
        LEFT JOIN (
            SELECT
                shop_id,
                UPPER(`schema`) AS fulfillment_type,
                posting_number,
                nm_id AS sku,
                COUNT(DISTINCT return_id) AS return_cnt,
                SUM(COALESCE(quantity, 0)) AS return_qty,
                MIN(return_date) AS first_return_date,
                MAX(ready_to_pickup_at) AS last_ready_to_pickup_at,
                MAX(picked_up_at) AS last_picked_up_at
            FROM dwd_ozon_return_detail
            WHERE posting_number IS NOT NULL
              AND `schema` IS NOT NULL
            GROUP BY shop_id, UPPER(`schema`), posting_number, nm_id
        ) AS ret
          ON ret.shop_id = ord.shop_id
         AND ret.fulfillment_type = ord.fulfillment_type
         AND ret.posting_number = ord.posting_number
         AND ret.sku = ord.sku
        LEFT JOIN (
            SELECT
                ranked.shop_id,
                ranked.fulfillment_type,
                ranked.posting_number,
                ranked.sku,
                ranked.return_id AS latest_return_id,
                ranked.status_sys_name AS latest_return_status_sys_name,
                ranked.status_display_name_cn
                    AS latest_return_status_display_name_cn,
                ranked.status_change_at AS latest_return_status_change_at,
                ranked.return_reason_name_cn AS latest_return_reason_name_cn
            FROM (
                SELECT
                    shop_id,
                    UPPER(`schema`) AS fulfillment_type,
                    posting_number,
                    nm_id AS sku,
                    return_id,
                    status_sys_name,
                    status_display_name_cn,
                    status_change_at,
                    return_reason_name_cn,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            shop_id,
                            UPPER(`schema`),
                            posting_number,
                            nm_id
                        ORDER BY
                            COALESCE(
                                status_change_at,
                                return_date,
                                order_date
                            ) DESC,
                            return_id DESC
                    ) AS row_num
                FROM dwd_ozon_return_detail
                WHERE posting_number IS NOT NULL
                  AND `schema` IS NOT NULL
            ) AS ranked
            WHERE ranked.row_num = 1
        ) AS latest
          ON latest.shop_id = ord.shop_id
         AND latest.fulfillment_type = ord.fulfillment_type
         AND latest.posting_number = ord.posting_number
         AND latest.sku = ord.sku
        WHERE ord.in_process_date BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR ord.shop_id = :shop_id)
        ON DUPLICATE KEY UPDATE
            order_id = VALUES(order_id),
            order_number = VALUES(order_number),
            offer_id = VALUES(offer_id),
            product_name = VALUES(product_name),
            product_name_cn = VALUES(product_name_cn),
            quantity = VALUES(quantity),
            status_code = VALUES(status_code),
            substatus_code = VALUES(substatus_code),
            status_name_cn = VALUES(status_name_cn),
            in_process_at = VALUES(in_process_at),
            shipment_date = VALUES(shipment_date),
            transferred_to_delivery_at = VALUES(transferred_to_delivery_at),
            delivery_date = VALUES(delivery_date),
            promised_delivery_at = VALUES(promised_delivery_at),
            cancellation_at = VALUES(cancellation_at),
            return_cnt = VALUES(return_cnt),
            return_qty = VALUES(return_qty),
            first_return_date = VALUES(first_return_date),
            latest_return_id = VALUES(latest_return_id),
            latest_return_status_sys_name =
                VALUES(latest_return_status_sys_name),
            latest_return_status_display_name_cn =
                VALUES(latest_return_status_display_name_cn),
            latest_return_status_change_at =
                VALUES(latest_return_status_change_at),
            latest_return_reason_name_cn =
                VALUES(latest_return_reason_name_cn),
            last_ready_to_pickup_at = VALUES(last_ready_to_pickup_at),
            last_picked_up_at = VALUES(last_picked_up_at),
            update_time = CURRENT_TIMESTAMP
        """
    )

    _delete_stale_statement = text(
        """
        DELETE target
        FROM dwm_ozon_order_lifecycle_detail AS target
        WHERE DATE(target.in_process_at) BETWEEN :date_from AND :date_to
          AND (:shop_id IS NULL OR target.shop_id = :shop_id)
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_order_detail AS ord
              WHERE ord.shop_id = target.shop_id
                AND ord.fulfillment_type = target.fulfillment_type
                AND ord.posting_number = target.posting_number
                AND ord.sku = target.sku
                AND ord.in_process_date BETWEEN :date_from AND :date_to
          )
        """
    )

    _unmatched_return_statement = text(
        """
        SELECT COUNT(*)
        FROM dwd_ozon_return_detail AS ret
        WHERE ret.order_date >= :date_from
          AND ret.order_date < DATE_ADD(:date_to, INTERVAL 1 DAY)
          AND (:shop_id IS NULL OR ret.shop_id = :shop_id)
          AND NOT EXISTS (
              SELECT 1
              FROM dwd_ozon_order_detail AS ord
              WHERE ord.shop_id = ret.shop_id
                AND ord.fulfillment_type = UPPER(ret.`schema`)
                AND ord.posting_number = ret.posting_number
                AND ord.sku = ret.nm_id
          )
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
        unmatched_result = await db.execute(self._unmatched_return_statement, params)
        await db.flush()
        return {
            "affected_rows": max(refresh_result.rowcount or 0, 0),
            "deleted_stale_rows": max(stale_result.rowcount or 0, 0),
            "unmatched_return_rows": int(unmatched_result.scalar_one()),
        }

    async def get_source_date_bounds(
        self, db: AsyncSession
    ) -> tuple[Optional[date], Optional[date]]:
        """Return the inclusive order-date coverage available in DWD."""
        row = (await db.execute(self._source_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]

    async def get_target_date_bounds(
        self, db: AsyncSession
    ) -> tuple[Optional[date], Optional[date]]:
        """Return the inclusive order-date coverage already present in this DWM."""
        row = (await db.execute(self._target_date_bounds_statement)).mappings().one()
        return row["date_from"], row["date_to"]


crud_dwm_ozon_order_lifecycle_detail = CRUDDWMOzonOrderLifecycleDetail()
