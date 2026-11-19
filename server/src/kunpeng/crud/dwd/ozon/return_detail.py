"""Build and query the Ozon return DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import (Select, String, cast, false, func, or_, select, text,
                        tuple_)
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon import DWDOzonReturnDetail
from kunpeng.models.ods.ozon.returns import ODSOzonReturn, ODSOzonReturnProduct
from kunpeng.schemas.ozon_return import OzonReturnKey


class CRUDDWDOzonReturnDetail:
    """Idempotently reconcile Ozon return-product details from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_ozon_return_detail (
            shop_id,
            return_id,
            nm_id,
            brand_name,
            category_name,
            product_name,
            product_barcode,
            offer_id,
            logistic_barcode,
            exemplar_id,
            status_id,
            status_display_name,
            status_sys_name,
            status_change_at,
            compensation_status_id,
            compensation_status_display_name,
            compensation_status_sys_name,
            compensation_status_change_at,
            buyer_comment,
            ready_to_pickup_at,
            picked_up_at,
            storage_expire_at,
            utilization_forecast_at,
            storage_days,
            pickup_duration_hours,
            order_date,
            return_reason_name,
            posting_number,
            order_id,
            order_number,
            srid,
            place_id,
            place_name,
            place_address,
            target_place_id,
            target_place_name,
            target_place_address,
            return_type,
            `schema`,
            return_date,
            is_opened,
            is_super_econom,
            quantity,
            price_amount,
            price_currency,
            storage_fee_amount,
            storage_fee_currency,
            utilization_fee_amount,
            utilization_fee_currency,
            commission_percent,
            commission_amount,
            commission_currency,
            price_without_commission_amount,
            price_without_commission_currency
        )
        SELECT
            source_shop_id,
            source_return_id,
            source_nm_id,
            source_brand_name,
            source_category_name,
            source_product_name,
            source_product_barcode,
            source_offer_id,
            source_logistic_barcode,
            source_exemplar_id,
            source_status_id,
            source_status_display_name,
            source_status_sys_name,
            source_status_change_at,
            source_compensation_status_id,
            source_compensation_status_display_name,
            source_compensation_status_sys_name,
            source_compensation_status_change_at,
            source_buyer_comment,
            source_ready_to_pickup_at,
            source_picked_up_at,
            source_storage_expire_at,
            source_utilization_forecast_at,
            source_storage_days,
            source_pickup_duration_hours,
            source_order_date,
            source_return_reason_name,
            source_posting_number,
            source_order_id,
            source_order_number,
            source_srid,
            source_place_id,
            source_place_name,
            source_place_address,
            source_target_place_id,
            source_target_place_name,
            source_target_place_address,
            source_return_type,
            source_schema,
            source_return_date,
            source_is_opened,
            source_is_super_econom,
            source_quantity,
            source_price_amount,
            source_price_currency,
            source_storage_fee_amount,
            source_storage_fee_currency,
            source_utilization_fee_amount,
            source_utilization_fee_currency,
            source_commission_percent,
            source_commission_amount,
            source_commission_currency,
            source_price_without_commission_amount,
            source_price_without_commission_currency
        FROM (
            SELECT
                r.shop_id AS source_shop_id,
                r.return_id AS source_return_id,
                p.sku AS source_nm_id,
                NULL AS source_brand_name,
                catalog.category_name AS source_category_name,
                COALESCE(p.product_name, catalog.product_name) AS source_product_name,
                catalog.product_barcode AS source_product_barcode,
                p.offer_id AS source_offer_id,
                r.logistic_barcode AS source_logistic_barcode,
                p.exemplar_id AS source_exemplar_id,
                r.status_id AS source_status_id,
                r.status_display_name AS source_status_display_name,
                r.status_sys_name AS source_status_sys_name,
                r.status_change_moment AS source_status_change_at,
                r.compensation_status_id AS source_compensation_status_id,
                r.compensation_status_display_name
                    AS source_compensation_status_display_name,
                r.compensation_status_sys_name
                    AS source_compensation_status_sys_name,
                r.compensation_status_change_moment
                    AS source_compensation_status_change_at,
                r.buyer_comment AS source_buyer_comment,
                storage.arrived_moment AS source_ready_to_pickup_at,
                r.logistic_final_moment AS source_picked_up_at,
                storage.tariffication_first_date AS source_storage_expire_at,
                storage.utilization_forecast_date AS source_utilization_forecast_at,
                storage.storage_days AS source_storage_days,
                CASE
                    WHEN storage.arrived_moment IS NOT NULL
                     AND r.logistic_final_moment IS NOT NULL
                     AND r.logistic_final_moment >= storage.arrived_moment
                    THEN ROUND(
                        TIMESTAMPDIFF(
                            MINUTE,
                            storage.arrived_moment,
                            r.logistic_final_moment
                        ) / 60,
                        2
                    )
                    ELSE NULL
                END AS source_pickup_duration_hours,
                COALESCE(fbo.created_at, fbs.in_process_at) AS source_order_date,
                r.return_reason_name AS source_return_reason_name,
                r.posting_number AS source_posting_number,
                r.order_id AS source_order_id,
                r.order_number AS source_order_number,
                r.order_number AS source_srid,
                r.place_id AS source_place_id,
                r.place_name AS source_place_name,
                r.place_address AS source_place_address,
                r.target_place_id AS source_target_place_id,
                r.target_place_name AS source_target_place_name,
                r.target_place_address AS source_target_place_address,
                r.type AS source_return_type,
                r.`schema` AS source_schema,
                r.return_date AS source_return_date,
                r.is_opened AS source_is_opened,
                r.is_super_econom AS source_is_super_econom,
                p.quantity AS source_quantity,
                p.price_amount AS source_price_amount,
                p.price_currency AS source_price_currency,
                storage.storage_fee_amount AS source_storage_fee_amount,
                storage.storage_fee_currency AS source_storage_fee_currency,
                storage.utilization_fee_amount AS source_utilization_fee_amount,
                storage.utilization_fee_currency
                    AS source_utilization_fee_currency,
                p.commission_percent AS source_commission_percent,
                p.commission_amount AS source_commission_amount,
                p.commission_currency AS source_commission_currency,
                p.price_without_commission_amount
                    AS source_price_without_commission_amount,
                p.price_without_commission_currency
                    AS source_price_without_commission_currency
            FROM ods_ozon_returns AS r
            INNER JOIN ods_ozon_return_products AS p
                ON p.shop_id = r.shop_id
               AND p.return_id = r.return_id
            LEFT JOIN ods_ozon_return_storage AS storage
                ON storage.shop_id = r.shop_id
               AND storage.return_id = r.return_id
            LEFT JOIN (
                SELECT
                    shop_id,
                    sku,
                    MAX(category_name) AS category_name,
                    MAX(name) AS product_name,
                    MAX(barcode) AS product_barcode
                FROM ods_ozon_products
                WHERE sku IS NOT NULL
                GROUP BY shop_id, sku
            ) AS catalog
                ON catalog.shop_id = p.shop_id
               AND catalog.sku = p.sku
            LEFT JOIN ods_ozon_fbo_postings AS fbo
                ON fbo.shop_id = r.shop_id
               AND fbo.posting_number = r.posting_number
            LEFT JOIN ods_ozon_fbs_postings AS fbs
                ON fbs.shop_id = r.shop_id
               AND fbs.posting_number = r.posting_number
            WHERE r.return_id IS NOT NULL
              AND p.sku IS NOT NULL
              AND (:shop_id IS NULL OR r.shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            brand_name = source_brand_name,
            category_name_cn = IF(
                NOT (category_name <=> source_category_name), NULL, category_name_cn
            ),
            category_name = source_category_name,
            product_name_cn = IF(
                NOT (product_name <=> source_product_name), NULL, product_name_cn
            ),
            product_name = source_product_name,
            product_barcode = source_product_barcode,
            offer_id = source_offer_id,
            logistic_barcode = source_logistic_barcode,
            exemplar_id = source_exemplar_id,
            status_id = source_status_id,
            status_display_name_cn = IF(
                NOT (status_display_name <=> source_status_display_name),
                NULL,
                status_display_name_cn
            ),
            status_display_name = source_status_display_name,
            status_sys_name = source_status_sys_name,
            status_change_at = source_status_change_at,
            compensation_status_id = source_compensation_status_id,
            compensation_status_display_name_cn = IF(
                NOT (
                    compensation_status_display_name
                    <=> source_compensation_status_display_name
                ),
                NULL,
                compensation_status_display_name_cn
            ),
            compensation_status_display_name =
                source_compensation_status_display_name,
            compensation_status_sys_name = source_compensation_status_sys_name,
            compensation_status_change_at = source_compensation_status_change_at,
            buyer_comment_cn = IF(
                NOT (buyer_comment <=> source_buyer_comment),
                NULL,
                buyer_comment_cn
            ),
            buyer_comment = source_buyer_comment,
            ready_to_pickup_at = source_ready_to_pickup_at,
            picked_up_at = source_picked_up_at,
            storage_expire_at = source_storage_expire_at,
            utilization_forecast_at = source_utilization_forecast_at,
            storage_days = source_storage_days,
            pickup_duration_hours = source_pickup_duration_hours,
            order_date = source_order_date,
            return_reason_name_cn = IF(
                NOT (return_reason_name <=> source_return_reason_name),
                NULL,
                return_reason_name_cn
            ),
            return_reason_name = source_return_reason_name,
            posting_number = source_posting_number,
            order_id = source_order_id,
            order_number = source_order_number,
            srid = source_srid,
            place_id = source_place_id,
            place_name_cn = IF(
                NOT (place_name <=> source_place_name), NULL, place_name_cn
            ),
            place_name = source_place_name,
            place_address_cn = IF(
                NOT (place_address <=> source_place_address), NULL, place_address_cn
            ),
            place_address = source_place_address,
            target_place_id = source_target_place_id,
            target_place_name_cn = IF(
                NOT (target_place_name <=> source_target_place_name),
                NULL,
                target_place_name_cn
            ),
            target_place_name = source_target_place_name,
            target_place_address_cn = IF(
                NOT (target_place_address <=> source_target_place_address),
                NULL,
                target_place_address_cn
            ),
            target_place_address = source_target_place_address,
            return_type = source_return_type,
            `schema` = source_schema,
            return_date = source_return_date,
            is_opened = source_is_opened,
            is_super_econom = source_is_super_econom,
            quantity = source_quantity,
            price_amount = source_price_amount,
            price_currency = source_price_currency,
            storage_fee_amount = source_storage_fee_amount,
            storage_fee_currency = source_storage_fee_currency,
            utilization_fee_amount = source_utilization_fee_amount,
            utilization_fee_currency = source_utilization_fee_currency,
            commission_percent = source_commission_percent,
            commission_amount = source_commission_amount,
            commission_currency = source_commission_currency,
            price_without_commission_amount =
                source_price_without_commission_amount,
            price_without_commission_currency =
                source_price_without_commission_currency
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new return-product rows and refresh existing DWD rows."""
        source_count = (
            select(func.count())
            .select_from(ODSOzonReturn)
            .join(
                ODSOzonReturnProduct,
                (ODSOzonReturnProduct.shop_id == ODSOzonReturn.shop_id)
                & (ODSOzonReturnProduct.return_id == ODSOzonReturn.return_id),
            )
            .where(
                ODSOzonReturn.return_id.is_not(None),
                ODSOzonReturnProduct.sku.is_not(None),
            )
        )
        if shop_id is not None:
            source_count = source_count.where(ODSOzonReturn.shop_id == shop_id)

        count = int((await db.execute(source_count)).scalar_one())
        if count == 0:
            return {"source_count": 0, "affected_rows": 0}

        result = await db.execute(self._upsert_statement, {"shop_id": shop_id})
        await db.flush()
        return {
            "source_count": count,
            "affected_rows": max(result.rowcount or 0, 0),
        }

    def _apply_filters(
        self,
        query: Select[Any],
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        order_from: Optional[datetime] = None,
        order_to: Optional[datetime] = None,
        return_id: Optional[int] = None,
        nm_id: Optional[int] = None,
        posting_number: Optional[str] = None,
        order_id: Optional[int] = None,
        order_number: Optional[str] = None,
        offer_id: Optional[str] = None,
        brand_name: Optional[str] = None,
        category_name: Optional[str] = None,
        product_name: Optional[str] = None,
        status: Optional[str] = None,
        return_type: Optional[str] = None,
        schema: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDOzonReturnDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if order_from is not None:
            query = query.where(model.order_date >= order_from)
        if order_to is not None:
            query = query.where(model.order_date < order_to)
        if return_id is not None:
            query = query.where(model.return_id == return_id)
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
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
        if offer_id:
            query = query.where(
                model.offer_id.contains(offer_id.strip(), autoescape=True)
            )
        if brand_name:
            query = query.where(
                model.brand_name.contains(brand_name.strip(), autoescape=True)
            )
        if category_name:
            normalized_category = category_name.strip()
            query = query.where(
                or_(
                    model.category_name.contains(normalized_category, autoescape=True),
                    model.category_name_cn.contains(
                        normalized_category, autoescape=True
                    ),
                )
            )
        if product_name:
            normalized_product = product_name.strip()
            query = query.where(
                or_(
                    model.product_name.contains(normalized_product, autoescape=True),
                    model.product_name_cn.contains(normalized_product, autoescape=True),
                )
            )
        if status:
            normalized_status = status.strip()
            query = query.where(
                or_(
                    model.status_display_name.contains(
                        normalized_status, autoescape=True
                    ),
                    model.status_display_name_cn.contains(
                        normalized_status, autoescape=True
                    ),
                    model.status_sys_name.contains(normalized_status, autoescape=True),
                )
            )
        if return_type:
            query = query.where(
                model.return_type.contains(return_type.strip(), autoescape=True)
            )
        if schema:
            query = query.where(model.schema.contains(schema.strip(), autoescape=True))
        if keyword:
            normalized_keyword = keyword.strip()
            query = query.where(
                or_(
                    cast(model.return_id, String).contains(
                        normalized_keyword, autoescape=True
                    ),
                    cast(model.nm_id, String).contains(
                        normalized_keyword, autoescape=True
                    ),
                    cast(model.order_id, String).contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.product_name.contains(normalized_keyword, autoescape=True),
                    model.product_name_cn.contains(normalized_keyword, autoescape=True),
                    model.product_barcode.contains(normalized_keyword, autoescape=True),
                    model.offer_id.contains(normalized_keyword, autoescape=True),
                    model.logistic_barcode.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.posting_number.contains(normalized_keyword, autoescape=True),
                    model.order_number.contains(normalized_keyword, autoescape=True),
                    model.srid.contains(normalized_keyword, autoescape=True),
                    model.return_reason_name.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.return_reason_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.compensation_status_display_name.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.compensation_status_display_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.buyer_comment.contains(normalized_keyword, autoescape=True),
                    model.buyer_comment_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.place_name.contains(normalized_keyword, autoescape=True),
                    model.place_name_cn.contains(normalized_keyword, autoescape=True),
                    model.place_address.contains(normalized_keyword, autoescape=True),
                    model.place_address_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.target_place_name.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.target_place_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.target_place_address.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.target_place_address_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                )
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDOzonReturnDetail
        order_date_order = (
            model.order_date.asc() if sort_order == "asc" else model.order_date.desc()
        )
        return_date_order = (
            model.return_date.asc() if sort_order == "asc" else model.return_date.desc()
        )
        return query.order_by(
            order_date_order,
            return_date_order,
            model.shop_id.asc(),
            model.return_id.asc(),
            model.nm_id.asc(),
        )

    async def list_returns(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        page: int,
        page_size: int,
        sort_order: str = "desc",
        **filters: Any,
    ) -> tuple[list[DWDOzonReturnDetail], int]:
        """Return one stable page and its filtered row count."""
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDOzonReturnDetail),
            allowed_shop_ids=allowed_shop_ids,
            **filters,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(
            select(DWDOzonReturnDetail),
            allowed_shop_ids=allowed_shop_ids,
            **filters,
        )
        data_query = (
            self._ordered_query(data_query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await db.execute(data_query)).scalars().all()), total

    async def list_returns_for_export(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        sort_order: str = "desc",
        **filters: Any,
    ) -> list[DWDOzonReturnDetail]:
        """Return all filtered rows for Excel export."""
        query = self._apply_filters(
            select(DWDOzonReturnDetail),
            allowed_shop_ids=allowed_shop_ids,
            **filters,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_returns_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonReturnKey],
    ) -> list[DWDOzonReturnDetail]:
        """Return selected rows while enforcing the caller's Ozon shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.return_id, key.nm_id) for key in keys]
        model = DWDOzonReturnDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.return_id, model.nm_id).in_(composite_keys),
        )
        return list(
            (await db.execute(self._ordered_query(query, sort_order="desc")))
            .scalars()
            .all()
        )


crud_dwd_ozon_return_detail = CRUDDWDOzonReturnDetail()
