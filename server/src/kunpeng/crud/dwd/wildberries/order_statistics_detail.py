"""Build and query the Wildberries statistics order DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.order_statistics_detail import (
    DWDWBOrderStatisticsDetail,
)
from kunpeng.models.ods.wildberries.sales import ODSWBSupplierOrder
from kunpeng.schemas.wb_order_statistics import WBOrderStatisticsKey


class CRUDDWDWBOrderStatisticsDetail:
    """Idempotently reconcile one DWD row per Statistics API order."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_wb_order_statistics_detail (
            shop_id,
            srid,
            order_date,
            last_change_date,
            warehouse_name,
            country_name,
            oblast_okrug_name,
            region_name,
            supplier_article,
            nm_id,
            barcode_ori,
            barcode_hand,
            category,
            subject_name,
            tech_size,
            total_price,
            discount_percent,
            price_with_disc,
            finished_price,
            is_cancel,
            cancel_date,
            sticker_id,
            g_number
        )
        SELECT
            source_shop_id,
            source_srid,
            source_order_date,
            source_last_change_date,
            source_warehouse_name,
            source_country_name,
            source_oblast_okrug_name,
            source_region_name,
            source_supplier_article,
            source_nm_id,
            source_barcode_ori,
            source_barcode_hand,
            source_category,
            source_subject_name,
            source_tech_size,
            source_total_price,
            source_discount_percent,
            source_price_with_disc,
            source_finished_price,
            source_is_cancel,
            source_cancel_date,
            source_sticker_id,
            source_g_number
        FROM (
            SELECT
                stats_order.shop_id AS source_shop_id,
                stats_order.srid AS source_srid,
                stats_order.date AS source_order_date,
                stats_order.last_change_date AS source_last_change_date,
                stats_order.warehouse_name AS source_warehouse_name,
                stats_order.country_name AS source_country_name,
                stats_order.oblast_okrug_name AS source_oblast_okrug_name,
                stats_order.region_name AS source_region_name,
                stats_order.supplier_article AS source_supplier_article,
                stats_order.nm_id AS source_nm_id,
                CASE
                    WHEN TRIM(stats_order.barcode) REGEXP '^[0-9]{13}$'
                    THEN TRIM(stats_order.barcode)
                    ELSE NULL
                END AS source_barcode_ori,
                CASE
                    WHEN TRIM(stats_order.barcode) REGEXP '^[A-Za-z0-9_-]+$'
                     AND TRIM(stats_order.barcode) REGEXP '[A-Za-z]'
                     AND TRIM(stats_order.barcode) REGEXP '[0-9]'
                    THEN TRIM(stats_order.barcode)
                    ELSE NULL
                END AS source_barcode_hand,
                stats_order.category AS source_category,
                stats_order.subject AS source_subject_name,
                stats_order.tech_size AS source_tech_size,
                stats_order.total_price AS source_total_price,
                stats_order.discount_percent AS source_discount_percent,
                stats_order.price_with_disc AS source_price_with_disc,
                stats_order.finished_price AS source_finished_price,
                stats_order.is_cancel AS source_is_cancel,
                stats_order.cancel_date AS source_cancel_date,
                stats_order.sticker AS source_sticker_id,
                stats_order.g_number AS source_g_number
            FROM ods_wb_supplier_orders AS stats_order
            WHERE stats_order.srid IS NOT NULL
              AND stats_order.srid <> ''
              AND (:shop_id IS NULL OR stats_order.shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            order_date = source_order_date,
            last_change_date = source_last_change_date,
            warehouse_name_cn = IF(
                NOT (warehouse_name <=> source_warehouse_name),
                NULL,
                warehouse_name_cn
            ),
            warehouse_name = source_warehouse_name,
            country_name_cn = IF(
                NOT (country_name <=> source_country_name), NULL, country_name_cn
            ),
            country_name = source_country_name,
            oblast_okrug_name_cn = IF(
                NOT (oblast_okrug_name <=> source_oblast_okrug_name),
                NULL,
                oblast_okrug_name_cn
            ),
            oblast_okrug_name = source_oblast_okrug_name,
            region_name_cn = IF(
                NOT (region_name <=> source_region_name), NULL, region_name_cn
            ),
            region_name = source_region_name,
            supplier_article = source_supplier_article,
            nm_id = source_nm_id,
            barcode_ori = source_barcode_ori,
            barcode_hand = source_barcode_hand,
            category_cn = IF(
                NOT (category <=> source_category), NULL, category_cn
            ),
            category = source_category,
            subject_name_cn = IF(
                NOT (subject_name <=> source_subject_name), NULL, subject_name_cn
            ),
            subject_name = source_subject_name,
            tech_size_cn = IF(
                NOT (tech_size <=> source_tech_size), NULL, tech_size_cn
            ),
            tech_size = source_tech_size,
            total_price = source_total_price,
            discount_percent = source_discount_percent,
            price_with_disc = source_price_with_disc,
            finished_price = source_finished_price,
            is_cancel = source_is_cancel,
            cancel_date = source_cancel_date,
            sticker_id = source_sticker_id,
            g_number = source_g_number
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new statistics orders and refresh existing DWD rows."""
        source_count = (
            select(func.count())
            .select_from(ODSWBSupplierOrder)
            .where(
                ODSWBSupplierOrder.srid.is_not(None),
                ODSWBSupplierOrder.srid != "",
            )
        )
        if shop_id is not None:
            source_count = source_count.where(ODSWBSupplierOrder.shop_id == shop_id)

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
        srid: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        country_name: Optional[str] = None,
        oblast_okrug_name: Optional[str] = None,
        region_name: Optional[str] = None,
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        category: Optional[str] = None,
        subject_name: Optional[str] = None,
        is_cancel: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDWBOrderStatisticsDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if order_from is not None:
            query = query.where(model.order_date >= order_from)
        if order_to is not None:
            query = query.where(model.order_date < order_to)
        if srid:
            query = query.where(model.srid.contains(srid.strip(), autoescape=True))
        if warehouse_name:
            normalized_warehouse = warehouse_name.strip()
            query = query.where(
                or_(
                    model.warehouse_name.contains(
                        normalized_warehouse, autoescape=True
                    ),
                    model.warehouse_name_cn.contains(
                        normalized_warehouse, autoescape=True
                    ),
                )
            )
        if country_name:
            normalized_country = country_name.strip()
            query = query.where(
                or_(
                    model.country_name.contains(normalized_country, autoescape=True),
                    model.country_name_cn.contains(normalized_country, autoescape=True),
                )
            )
        if oblast_okrug_name:
            normalized_okrug = oblast_okrug_name.strip()
            query = query.where(
                or_(
                    model.oblast_okrug_name.contains(normalized_okrug, autoescape=True),
                    model.oblast_okrug_name_cn.contains(
                        normalized_okrug, autoescape=True
                    ),
                )
            )
        if region_name:
            normalized_region = region_name.strip()
            query = query.where(
                or_(
                    model.region_name.contains(normalized_region, autoescape=True),
                    model.region_name_cn.contains(normalized_region, autoescape=True),
                )
            )
        if supplier_article:
            query = query.where(
                model.supplier_article.contains(
                    supplier_article.strip(), autoescape=True
                )
            )
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
        if category:
            normalized_category = category.strip()
            query = query.where(
                or_(
                    model.category.contains(normalized_category, autoescape=True),
                    model.category_cn.contains(normalized_category, autoescape=True),
                )
            )
        if subject_name:
            normalized_subject = subject_name.strip()
            query = query.where(
                or_(
                    model.subject_name.contains(normalized_subject, autoescape=True),
                    model.subject_name_cn.contains(normalized_subject, autoescape=True),
                )
            )
        if is_cancel is not None:
            query = query.where(model.is_cancel == is_cancel)
        if keyword:
            normalized_keyword = keyword.strip()
            query = query.where(
                or_(
                    model.srid.contains(normalized_keyword, autoescape=True),
                    model.warehouse_name.contains(normalized_keyword, autoescape=True),
                    model.warehouse_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.country_name.contains(normalized_keyword, autoescape=True),
                    model.country_name_cn.contains(normalized_keyword, autoescape=True),
                    model.oblast_okrug_name.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.oblast_okrug_name_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.region_name.contains(normalized_keyword, autoescape=True),
                    model.region_name_cn.contains(normalized_keyword, autoescape=True),
                    model.supplier_article.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.barcode_ori.contains(normalized_keyword, autoescape=True),
                    model.barcode_hand.contains(normalized_keyword, autoescape=True),
                    model.category.contains(normalized_keyword, autoescape=True),
                    model.category_cn.contains(normalized_keyword, autoescape=True),
                    model.subject_name.contains(normalized_keyword, autoescape=True),
                    model.subject_name_cn.contains(normalized_keyword, autoescape=True),
                    model.tech_size.contains(normalized_keyword, autoescape=True),
                    model.tech_size_cn.contains(normalized_keyword, autoescape=True),
                    model.sticker_id.contains(normalized_keyword, autoescape=True),
                    model.g_number.contains(normalized_keyword, autoescape=True),
                )
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDWBOrderStatisticsDetail
        order_time = (
            model.order_date.asc() if sort_order == "asc" else model.order_date.desc()
        )
        return query.order_by(order_time, model.shop_id.asc(), model.srid.asc())

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
        srid: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        country_name: Optional[str] = None,
        oblast_okrug_name: Optional[str] = None,
        region_name: Optional[str] = None,
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        category: Optional[str] = None,
        subject_name: Optional[str] = None,
        is_cancel: Optional[bool] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> tuple[list[DWDWBOrderStatisticsDetail], int]:
        """Return one stable page and the filtered row count."""
        filter_args = {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": shop_id,
            "order_from": order_from,
            "order_to": order_to,
            "srid": srid,
            "warehouse_name": warehouse_name,
            "country_name": country_name,
            "oblast_okrug_name": oblast_okrug_name,
            "region_name": region_name,
            "supplier_article": supplier_article,
            "nm_id": nm_id,
            "category": category,
            "subject_name": subject_name,
            "is_cancel": is_cancel,
            "keyword": keyword,
        }
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDWBOrderStatisticsDetail),
            **filter_args,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(
            select(DWDWBOrderStatisticsDetail), **filter_args
        )
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
        srid: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        country_name: Optional[str] = None,
        oblast_okrug_name: Optional[str] = None,
        region_name: Optional[str] = None,
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        category: Optional[str] = None,
        subject_name: Optional[str] = None,
        is_cancel: Optional[bool] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> list[DWDWBOrderStatisticsDetail]:
        """Return all filtered rows for server-side Excel export."""
        query = self._apply_filters(
            select(DWDWBOrderStatisticsDetail),
            allowed_shop_ids=allowed_shop_ids,
            shop_id=shop_id,
            order_from=order_from,
            order_to=order_to,
            srid=srid,
            warehouse_name=warehouse_name,
            country_name=country_name,
            oblast_okrug_name=oblast_okrug_name,
            region_name=region_name,
            supplier_article=supplier_article,
            nm_id=nm_id,
            category=category,
            subject_name=subject_name,
            is_cancel=is_cancel,
            keyword=keyword,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_orders_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBOrderStatisticsKey],
    ) -> list[DWDWBOrderStatisticsDetail]:
        """Return selected rows while enforcing the caller's shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.srid) for key in keys]
        model = DWDWBOrderStatisticsDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.srid).in_(composite_keys),
        )
        query = self._ordered_query(query, sort_order="desc")
        return list((await db.execute(query)).scalars().all())


crud_dwd_wb_order_statistics_detail = CRUDDWDWBOrderStatisticsDetail()
