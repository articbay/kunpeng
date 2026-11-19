"""Build and query the Wildberries order DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.order_detail import DWDWBOrderDetail
from kunpeng.models.ods.wildberries.marketplace import ODSWBMarketplaceOrder
from kunpeng.schemas.wb_order import WBOrderKey


class CRUDDWDWBOrderDetail:
    """Idempotently reconcile one DWD row per Marketplace order."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_wb_order_detail (
            shop_id,
            order_id,
            supply_id,
            sticker_id,
            order_dt,
            title,
            tech_size,
            color,
            barcode_ori,
            barcode_hand,
            retail_price,
            currency,
            nm_id,
            supplier_article,
            warehouse_id,
            warehouse_name,
            wb_status,
            address,
            is_b2b,
            delivery_type,
            supplier_status,
            is_cancellable,
            price,
            converted_price,
            currency_code,
            converted_currency_code,
            office_id,
            cargo_type,
            cross_border_type,
            is_zero_order
        )
        SELECT
            source_shop_id,
            source_order_id,
            source_supply_id,
            source_sticker_id,
            source_order_dt,
            source_title,
            source_tech_size,
            source_color,
            source_barcode_ori,
            source_barcode_hand,
            source_retail_price,
            source_currency,
            source_nm_id,
            source_supplier_article,
            source_warehouse_id,
            source_warehouse_name,
            source_wb_status,
            source_address,
            source_is_b2b,
            source_delivery_type,
            source_supplier_status,
            source_is_cancellable,
            source_price,
            source_converted_price,
            source_currency_code,
            source_converted_currency_code,
            source_office_id,
            source_cargo_type,
            source_cross_border_type,
            source_is_zero_order
        FROM (
            SELECT
                marketplace.shop_id AS source_shop_id,
                marketplace.order_id AS source_order_id,
                marketplace.supply_id AS source_supply_id,
                (
                    SELECT report.sticker_id
                    FROM ods_wb_sales_reports AS report
                    WHERE report.shop_id = marketplace.shop_id
                      AND report.order_id = marketplace.order_id
                      AND report.sticker_id IS NOT NULL
                      AND report.sticker_id <> ''
                    ORDER BY
                        report.rr_date DESC,
                        report.sale_dt DESC,
                        report.rrd_id DESC,
                        report.id DESC
                    LIMIT 1
                ) AS source_sticker_id,
                marketplace.created_at AS source_order_dt,
                (
                    SELECT funnel.title
                    FROM ods_wb_sales_funnels AS funnel
                    WHERE funnel.shop_id = marketplace.shop_id
                      AND funnel.nm_id = marketplace.nm_id
                      AND funnel.title IS NOT NULL
                      AND funnel.title <> ''
                    ORDER BY
                        funnel.date_to DESC,
                        funnel.date_from DESC,
                        funnel.id DESC
                    LIMIT 1
                ) AS source_title,
                (
                    SELECT stats_order.tech_size
                    FROM ods_wb_supplier_orders AS stats_order
                    WHERE stats_order.shop_id = marketplace.shop_id
                      AND stats_order.srid = marketplace.rid
                      AND stats_order.tech_size IS NOT NULL
                      AND stats_order.tech_size <> ''
                    ORDER BY
                        stats_order.last_change_date DESC,
                        stats_order.date DESC,
                        stats_order.id DESC
                    LIMIT 1
                ) AS source_tech_size,
                NULLIF(marketplace.color_code, '') AS source_color,
                (
                    SELECT TRIM(sku_values.barcode)
                    FROM JSON_TABLE(
                        COALESCE(marketplace.skus, JSON_ARRAY()),
                        '$[*]' COLUMNS (
                            position FOR ORDINALITY,
                            barcode VARCHAR(255) PATH '$'
                        )
                    ) AS sku_values
                    WHERE TRIM(sku_values.barcode) REGEXP '^[0-9]{13}$'
                    ORDER BY sku_values.position
                    LIMIT 1
                ) AS source_barcode_ori,
                (
                    SELECT TRIM(sku_values.barcode)
                    FROM JSON_TABLE(
                        COALESCE(marketplace.skus, JSON_ARRAY()),
                        '$[*]' COLUMNS (
                            position FOR ORDINALITY,
                            barcode VARCHAR(255) PATH '$'
                        )
                    ) AS sku_values
                    WHERE TRIM(sku_values.barcode) REGEXP '^[A-Za-z0-9_-]+$'
                      AND TRIM(sku_values.barcode) REGEXP '[A-Za-z]'
                      AND TRIM(sku_values.barcode) REGEXP '[0-9]'
                    ORDER BY sku_values.position
                    LIMIT 1
                ) AS source_barcode_hand,
                (
                    SELECT report.retail_price
                    FROM ods_wb_sales_reports AS report
                    WHERE report.shop_id = marketplace.shop_id
                      AND report.order_id = marketplace.order_id
                      AND report.retail_price IS NOT NULL
                    ORDER BY
                        report.rr_date DESC,
                        report.sale_dt DESC,
                        report.rrd_id DESC,
                        report.id DESC
                    LIMIT 1
                ) AS source_retail_price,
                (
                    SELECT report.currency
                    FROM ods_wb_sales_reports AS report
                    WHERE report.shop_id = marketplace.shop_id
                      AND report.order_id = marketplace.order_id
                      AND report.currency IS NOT NULL
                      AND report.currency <> ''
                    ORDER BY
                        report.rr_date DESC,
                        report.sale_dt DESC,
                        report.rrd_id DESC,
                        report.id DESC
                    LIMIT 1
                ) AS source_currency,
                marketplace.nm_id AS source_nm_id,
                marketplace.article AS source_supplier_article,
                marketplace.warehouse_id AS source_warehouse_id,
                (
                    SELECT stats_order.warehouse_name
                    FROM ods_wb_supplier_orders AS stats_order
                    WHERE stats_order.shop_id = marketplace.shop_id
                      AND stats_order.srid = marketplace.rid
                      AND stats_order.warehouse_name IS NOT NULL
                      AND stats_order.warehouse_name <> ''
                    ORDER BY
                        stats_order.last_change_date DESC,
                        stats_order.date DESC,
                        stats_order.id DESC
                    LIMIT 1
                ) AS source_warehouse_name,
                marketplace.wb_status AS source_wb_status,
                CASE
                    WHEN JSON_TYPE(marketplace.address) = 'OBJECT' THEN COALESCE(
                        NULLIF(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(
                                    marketplace.address,
                                    '$.fullAddress'
                                )
                            ),
                            ''
                        ),
                        NULLIF(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(marketplace.address, '$.address')
                            ),
                            ''
                        )
                    )
                    WHEN JSON_TYPE(marketplace.address) = 'STRING' THEN NULLIF(
                        JSON_UNQUOTE(marketplace.address),
                        ''
                    )
                    ELSE NULL
                END AS source_address,
                CASE LOWER(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(marketplace.options, '$.isB2B')
                    )
                )
                    WHEN 'true' THEN 1
                    WHEN 'false' THEN 0
                    ELSE NULL
                END AS source_is_b2b,
                marketplace.delivery_type AS source_delivery_type,
                marketplace.supplier_status AS source_supplier_status,
                marketplace.is_cancellable AS source_is_cancellable,
                marketplace.price AS source_price,
                marketplace.converted_price AS source_converted_price,
                marketplace.currency_code AS source_currency_code,
                marketplace.converted_currency_code
                    AS source_converted_currency_code,
                marketplace.office_id AS source_office_id,
                marketplace.cargo_type AS source_cargo_type,
                marketplace.cross_border_type AS source_cross_border_type,
                marketplace.is_zero_order AS source_is_zero_order
            FROM ods_wb_marketplace_orders AS marketplace
            WHERE marketplace.order_id IS NOT NULL
              AND (:shop_id IS NULL OR marketplace.shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            supply_id = source_supply_id,
            sticker_id = source_sticker_id,
            order_dt = source_order_dt,
            title_cn = IF(NOT (title <=> source_title), NULL, title_cn),
            title = source_title,
            tech_size_cn = IF(
                NOT (tech_size <=> source_tech_size), NULL, tech_size_cn
            ),
            tech_size = source_tech_size,
            color_cn = IF(NOT (color <=> source_color), NULL, color_cn),
            color = source_color,
            barcode_ori = source_barcode_ori,
            barcode_hand = source_barcode_hand,
            retail_price = source_retail_price,
            currency = source_currency,
            nm_id = source_nm_id,
            supplier_article = source_supplier_article,
            warehouse_id = source_warehouse_id,
            warehouse_name_cn = IF(
                NOT (warehouse_name <=> source_warehouse_name),
                NULL,
                warehouse_name_cn
            ),
            warehouse_name = source_warehouse_name,
            wb_status_cn = IF(
                NOT (wb_status <=> source_wb_status), NULL, wb_status_cn
            ),
            wb_status = source_wb_status,
            address_cn = IF(NOT (address <=> source_address), NULL, address_cn),
            address = source_address,
            is_b2b = source_is_b2b,
            delivery_type = source_delivery_type,
            supplier_status_cn = IF(
                NOT (supplier_status <=> source_supplier_status),
                NULL,
                supplier_status_cn
            ),
            supplier_status = source_supplier_status,
            is_cancellable = source_is_cancellable,
            price = source_price,
            converted_price = source_converted_price,
            currency_code = source_currency_code,
            converted_currency_code = source_converted_currency_code,
            office_id = source_office_id,
            cargo_type = source_cargo_type,
            cross_border_type = source_cross_border_type,
            is_zero_order = source_is_zero_order
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new Marketplace orders and refresh enriched DWD fields."""
        source_count = (
            select(func.count())
            .select_from(ODSWBMarketplaceOrder)
            .where(ODSWBMarketplaceOrder.order_id.is_not(None))
        )
        if shop_id is not None:
            source_count = source_count.where(ODSWBMarketplaceOrder.shop_id == shop_id)

        count = int((await db.execute(source_count)).scalar_one())
        if count == 0:
            return {"source_count": 0, "affected_rows": 0}

        result = await db.execute(self._upsert_statement, {"shop_id": shop_id})
        await db.commit()
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
        order_id: Optional[int] = None,
        supply_id: Optional[str] = None,
        sticker_id: Optional[str] = None,
        nm_id: Optional[int] = None,
        supplier_article: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        wb_status: Optional[str] = None,
        supplier_status: Optional[str] = None,
        delivery_type: Optional[str] = None,
        is_cancellable: Optional[bool] = None,
        is_b2b: Optional[bool] = None,
        is_zero_order: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDWBOrderDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if order_from is not None:
            query = query.where(model.order_dt >= order_from)
        if order_to is not None:
            query = query.where(model.order_dt < order_to)
        if order_id is not None:
            query = query.where(model.order_id == order_id)
        if supply_id:
            query = query.where(
                model.supply_id.contains(supply_id.strip(), autoescape=True)
            )
        if sticker_id:
            query = query.where(
                model.sticker_id.contains(sticker_id.strip(), autoescape=True)
            )
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
        if supplier_article:
            query = query.where(
                model.supplier_article.contains(
                    supplier_article.strip(), autoescape=True
                )
            )
        if warehouse_id is not None:
            query = query.where(model.warehouse_id == warehouse_id)
        if wb_status:
            normalized_status = wb_status.strip()
            query = query.where(
                or_(
                    model.wb_status.contains(normalized_status, autoescape=True),
                    model.wb_status_cn.contains(normalized_status, autoescape=True),
                )
            )
        if supplier_status:
            normalized_supplier_status = supplier_status.strip()
            query = query.where(
                or_(
                    model.supplier_status.contains(
                        normalized_supplier_status, autoescape=True
                    ),
                    model.supplier_status_cn.contains(
                        normalized_supplier_status, autoescape=True
                    ),
                )
            )
        if delivery_type:
            normalized_delivery_type = delivery_type.strip()
            query = query.where(
                model.delivery_type.contains(normalized_delivery_type, autoescape=True)
            )
        if is_cancellable is not None:
            query = query.where(model.is_cancellable == is_cancellable)
        if is_b2b is not None:
            query = query.where(model.is_b2b == is_b2b)
        if is_zero_order is not None:
            query = query.where(model.is_zero_order == is_zero_order)
        if keyword:
            normalized_keyword = keyword.strip()
            query = query.where(
                or_(
                    model.supply_id.contains(normalized_keyword, autoescape=True),
                    model.sticker_id.contains(normalized_keyword, autoescape=True),
                    model.title.contains(normalized_keyword, autoescape=True),
                    model.title_cn.contains(normalized_keyword, autoescape=True),
                    model.tech_size.contains(normalized_keyword, autoescape=True),
                    model.tech_size_cn.contains(normalized_keyword, autoescape=True),
                    model.color.contains(normalized_keyword, autoescape=True),
                    model.color_cn.contains(normalized_keyword, autoescape=True),
                    model.barcode_ori.contains(normalized_keyword, autoescape=True),
                    model.barcode_hand.contains(normalized_keyword, autoescape=True),
                    model.supplier_article.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.warehouse_name.contains(normalized_keyword, autoescape=True),
                    model.warehouse_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.address.contains(normalized_keyword, autoescape=True),
                    model.address_cn.contains(normalized_keyword, autoescape=True),
                    model.wb_status_cn.contains(normalized_keyword, autoescape=True),
                    model.supplier_status_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                )
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDWBOrderDetail
        order_time = (
            model.order_dt.asc() if sort_order == "asc" else model.order_dt.desc()
        )
        return query.order_by(order_time, model.shop_id.asc(), model.order_id.asc())

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        page: int,
        page_size: int,
        shop_id: Optional[int] = None,
        order_from: Optional[datetime] = None,
        order_to: Optional[datetime] = None,
        order_id: Optional[int] = None,
        supply_id: Optional[str] = None,
        sticker_id: Optional[str] = None,
        nm_id: Optional[int] = None,
        supplier_article: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        wb_status: Optional[str] = None,
        supplier_status: Optional[str] = None,
        delivery_type: Optional[str] = None,
        is_cancellable: Optional[bool] = None,
        is_b2b: Optional[bool] = None,
        is_zero_order: Optional[bool] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> tuple[list[DWDWBOrderDetail], int]:
        """Return one stable page and the filtered row count."""
        filter_args = {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": shop_id,
            "order_from": order_from,
            "order_to": order_to,
            "order_id": order_id,
            "supply_id": supply_id,
            "sticker_id": sticker_id,
            "nm_id": nm_id,
            "supplier_article": supplier_article,
            "warehouse_id": warehouse_id,
            "wb_status": wb_status,
            "supplier_status": supplier_status,
            "delivery_type": delivery_type,
            "is_cancellable": is_cancellable,
            "is_b2b": is_b2b,
            "is_zero_order": is_zero_order,
            "keyword": keyword,
        }
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDWBOrderDetail),
            **filter_args,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(select(DWDWBOrderDetail), **filter_args)
        data_query = (
            self._ordered_query(data_query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list((await db.execute(data_query)).scalars().all())
        return records, total

    async def list_orders_for_export(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        order_from: Optional[datetime] = None,
        order_to: Optional[datetime] = None,
        order_id: Optional[int] = None,
        supply_id: Optional[str] = None,
        sticker_id: Optional[str] = None,
        nm_id: Optional[int] = None,
        supplier_article: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        wb_status: Optional[str] = None,
        supplier_status: Optional[str] = None,
        delivery_type: Optional[str] = None,
        is_cancellable: Optional[bool] = None,
        is_b2b: Optional[bool] = None,
        is_zero_order: Optional[bool] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> list[DWDWBOrderDetail]:
        """Return all filtered rows for server-side Excel export."""
        query = self._apply_filters(
            select(DWDWBOrderDetail),
            allowed_shop_ids=allowed_shop_ids,
            shop_id=shop_id,
            order_from=order_from,
            order_to=order_to,
            order_id=order_id,
            supply_id=supply_id,
            sticker_id=sticker_id,
            nm_id=nm_id,
            supplier_article=supplier_article,
            warehouse_id=warehouse_id,
            wb_status=wb_status,
            supplier_status=supplier_status,
            delivery_type=delivery_type,
            is_cancellable=is_cancellable,
            is_b2b=is_b2b,
            is_zero_order=is_zero_order,
            keyword=keyword,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_orders_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBOrderKey],
    ) -> list[DWDWBOrderDetail]:
        """Return selected rows while enforcing the caller's shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.order_id) for key in keys]
        model = DWDWBOrderDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.order_id).in_(composite_keys),
        )
        query = self._ordered_query(query, sort_order="desc")
        return list((await db.execute(query)).scalars().all())


crud_dwd_wb_order_detail = CRUDDWDWBOrderDetail()
