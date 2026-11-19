"""Build and query the Wildberries return DWD table."""

from datetime import date
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.return_detail import DWDWBReturnDetail
from kunpeng.models.ods.wildberries.returns import ODSWBGoodsReturn
from kunpeng.schemas.wb_return import WBReturnKey


class CRUDDWDWBReturnDetail:
    """Idempotently reconcile return details from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_wb_return_detail (
            shop_id,
            brand,
            subject_name,
            barcode_ori,
            barcode_hand,
            nm_id,
            sticker_id,
            status,
            ready_to_return_dt,
            completed_dt,
            expired_dt,
            return_type,
            order_dt,
            reason,
            order_id,
            srid,
            dst_office_address,
            dst_office_id
        )
        SELECT
            source_shop_id,
            source_brand,
            source_subject_name,
            source_barcode_ori,
            source_barcode_hand,
            source_nm_id,
            source_sticker_id,
            source_status,
            source_ready_to_return_dt,
            source_completed_dt,
            source_expired_dt,
            source_return_type,
            source_order_dt,
            source_reason,
            source_order_id,
            source_srid,
            source_dst_office_address,
            source_dst_office_id
        FROM (
            SELECT
                shop_id AS source_shop_id,
                brand AS source_brand,
                subject_name AS source_subject_name,
                CASE
                    WHEN TRIM(barcode) REGEXP '^[0-9]{13}$'
                    THEN TRIM(barcode)
                    ELSE NULL
                END AS source_barcode_ori,
                CASE
                    WHEN TRIM(barcode) REGEXP '^[A-Za-z0-9_-]+$'
                     AND TRIM(barcode) REGEXP '[A-Za-z]'
                     AND TRIM(barcode) REGEXP '[0-9]'
                    THEN TRIM(barcode)
                    ELSE NULL
                END AS source_barcode_hand,
                nm_id AS source_nm_id,
                sticker_id AS source_sticker_id,
                status AS source_status,
                ready_to_return_dt AS source_ready_to_return_dt,
                completed_dt AS source_completed_dt,
                expired_dt AS source_expired_dt,
                return_type AS source_return_type,
                order_dt AS source_order_dt,
                reason AS source_reason,
                order_id AS source_order_id,
                srid AS source_srid,
                dst_office_address AS source_dst_office_address,
                dst_office_id AS source_dst_office_id
            FROM ods_wb_goods_returns
            WHERE srid IS NOT NULL
              AND (:shop_id IS NULL OR shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            brand = source_brand,
            subject_name_cn = IF(
                NOT (subject_name <=> source_subject_name), NULL, subject_name_cn
            ),
            subject_name = source_subject_name,
            barcode_ori = source_barcode_ori,
            barcode_hand = source_barcode_hand,
            nm_id = source_nm_id,
            sticker_id = source_sticker_id,
            status_cn = IF(NOT (status <=> source_status), NULL, status_cn),
            status = source_status,
            ready_to_return_dt = source_ready_to_return_dt,
            completed_dt = source_completed_dt,
            expired_dt = source_expired_dt,
            return_type_cn = IF(
                NOT (return_type <=> source_return_type), NULL, return_type_cn
            ),
            return_type = source_return_type,
            order_dt = source_order_dt,
            reason_cn = IF(NOT (reason <=> source_reason), NULL, reason_cn),
            reason = source_reason,
            order_id = source_order_id,
            dst_office_address_cn = IF(
                NOT (dst_office_address <=> source_dst_office_address),
                NULL,
                dst_office_address_cn
            ),
            dst_office_address = source_dst_office_address,
            dst_office_id = source_dst_office_id
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new returns and refresh existing DWD rows."""
        source_count = (
            select(func.count())
            .select_from(ODSWBGoodsReturn)
            .where(ODSWBGoodsReturn.srid.is_not(None))
        )
        if shop_id is not None:
            source_count = source_count.where(ODSWBGoodsReturn.shop_id == shop_id)

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
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        order_id: Optional[int] = None,
        brand: Optional[str] = None,
        subject_name: Optional[str] = None,
        status: Optional[str] = None,
        return_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDWBReturnDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if date_from is not None:
            query = query.where(model.order_dt >= date_from)
        if date_to is not None:
            query = query.where(model.order_dt <= date_to)
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
        if order_id is not None:
            query = query.where(model.order_id == order_id)
        if brand:
            query = query.where(model.brand.contains(brand.strip(), autoescape=True))
        if subject_name:
            normalized_subject = subject_name.strip()
            query = query.where(
                or_(
                    model.subject_name.contains(normalized_subject, autoescape=True),
                    model.subject_name_cn.contains(normalized_subject, autoescape=True),
                )
            )
        if status:
            normalized_status = status.strip()
            query = query.where(
                or_(
                    model.status.contains(normalized_status, autoescape=True),
                    model.status_cn.contains(normalized_status, autoescape=True),
                )
            )
        if return_type:
            normalized_return_type = return_type.strip()
            query = query.where(
                or_(
                    model.return_type.contains(normalized_return_type, autoescape=True),
                    model.return_type_cn.contains(
                        normalized_return_type, autoescape=True
                    ),
                )
            )
        if keyword:
            normalized_keyword = keyword.strip()
            query = query.where(
                or_(
                    model.barcode_ori.contains(normalized_keyword, autoescape=True),
                    model.barcode_hand.contains(normalized_keyword, autoescape=True),
                    model.sticker_id.contains(normalized_keyword, autoescape=True),
                    model.srid.contains(normalized_keyword, autoescape=True),
                    model.reason.contains(normalized_keyword, autoescape=True),
                    model.reason_cn.contains(normalized_keyword, autoescape=True),
                    model.dst_office_address.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.dst_office_address_cn.contains(
                        normalized_keyword, autoescape=True
                    ),
                    model.subject_name_cn.contains(normalized_keyword, autoescape=True),
                    model.status_cn.contains(normalized_keyword, autoescape=True),
                    model.return_type_cn.contains(normalized_keyword, autoescape=True),
                )
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDWBReturnDetail
        order_dt_order = (
            model.order_dt.asc() if sort_order == "asc" else model.order_dt.desc()
        )
        ready_time_order = (
            model.ready_to_return_dt.asc()
            if sort_order == "asc"
            else model.ready_to_return_dt.desc()
        )
        return query.order_by(
            order_dt_order,
            ready_time_order,
            model.shop_id.asc(),
            model.srid.asc(),
        )

    async def list_returns(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        page: int,
        page_size: int,
        shop_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        order_id: Optional[int] = None,
        brand: Optional[str] = None,
        subject_name: Optional[str] = None,
        status: Optional[str] = None,
        return_type: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> tuple[list[DWDWBReturnDetail], int]:
        """Return one stable page and the filtered row count."""
        filter_args = {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "nm_id": nm_id,
            "order_id": order_id,
            "brand": brand,
            "subject_name": subject_name,
            "status": status,
            "return_type": return_type,
            "keyword": keyword,
        }
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDWBReturnDetail),
            **filter_args,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(select(DWDWBReturnDetail), **filter_args)
        data_query = (
            self._ordered_query(data_query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list((await db.execute(data_query)).scalars().all())
        return records, total

    async def list_returns_for_export(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        order_id: Optional[int] = None,
        brand: Optional[str] = None,
        subject_name: Optional[str] = None,
        status: Optional[str] = None,
        return_type: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_order: str = "desc",
    ) -> list[DWDWBReturnDetail]:
        """Return all filtered rows for server-side Excel export."""
        query = self._apply_filters(
            select(DWDWBReturnDetail),
            allowed_shop_ids=allowed_shop_ids,
            shop_id=shop_id,
            date_from=date_from,
            date_to=date_to,
            nm_id=nm_id,
            order_id=order_id,
            brand=brand,
            subject_name=subject_name,
            status=status,
            return_type=return_type,
            keyword=keyword,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_returns_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBReturnKey],
    ) -> list[DWDWBReturnDetail]:
        """Return selected rows while enforcing the caller's shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.srid) for key in keys]
        model = DWDWBReturnDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.srid).in_(composite_keys),
        )
        query = self._ordered_query(query, sort_order="desc")
        return list((await db.execute(query)).scalars().all())


crud_dwd_wb_return_detail = CRUDDWDWBReturnDetail()
