"""Build and query the Ozon customer voice DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.ozon.customer_voice import DWDOzonCustomerVoiceDetail
from kunpeng.models.ods.ozon.reviews import ODSOzonReview
from kunpeng.schemas.ozon_customer_voice import OzonCustomerVoiceKey


class CRUDDWDOzonCustomerVoiceDetail:
    """Idempotently reconcile Ozon reviews and product dimensions from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_ozon_customer_voice_detail (
            shop_id, review_id, month, offer_id, sku,
            product_name, posting_number, order_status, review_text,
            published_at, review_status, rating, photos_amount,
            videos_amount, comments_amount
        )
        SELECT
            reviews.shop_id,
            reviews.review_id,
            DATE_FORMAT(
                DATE_ADD(reviews.published_at, INTERVAL 3 HOUR),
                '%Y-%m'
            ) AS month,
            products.offer_id,
            reviews.sku,
            COALESCE(reviews.product_name, products.product_name) AS product_name,
            NULL AS posting_number,
            reviews.order_status,
            reviews.text AS review_text,
            reviews.published_at,
            reviews.status AS review_status,
            reviews.rating,
            reviews.photos_amount,
            reviews.videos_amount,
            reviews.comments_amount
        FROM ods_ozon_reviews AS reviews
        LEFT JOIN (
            SELECT
                shop_id,
                sku,
                MAX(offer_id) AS offer_id,
                MAX(name) AS product_name
            FROM ods_ozon_products
            WHERE sku IS NOT NULL
            GROUP BY shop_id, sku
        ) AS products
          ON products.shop_id = reviews.shop_id
         AND products.sku = reviews.sku
        WHERE reviews.review_id IS NOT NULL
          AND (:shop_id IS NULL OR reviews.shop_id = :shop_id)
        ON DUPLICATE KEY UPDATE
            month = VALUES(month),
            offer_id = VALUES(offer_id),
            sku = VALUES(sku),
            product_name_cn = IF(
                NOT (
                    dwd_ozon_customer_voice_detail.product_name
                    <=> VALUES(product_name)
                ),
                NULL,
                dwd_ozon_customer_voice_detail.product_name_cn
            ),
            product_name = VALUES(product_name),
            posting_number = VALUES(posting_number),
            order_status_cn = IF(
                NOT (
                    dwd_ozon_customer_voice_detail.order_status
                    <=> VALUES(order_status)
                ),
                NULL,
                dwd_ozon_customer_voice_detail.order_status_cn
            ),
            order_status = VALUES(order_status),
            review_text_cn = IF(
                NOT (
                    dwd_ozon_customer_voice_detail.review_text
                    <=> VALUES(review_text)
                ),
                NULL,
                dwd_ozon_customer_voice_detail.review_text_cn
            ),
            review_text = VALUES(review_text),
            published_at = VALUES(published_at),
            review_status_cn = IF(
                NOT (
                    dwd_ozon_customer_voice_detail.review_status
                    <=> VALUES(review_status)
                ),
                NULL,
                dwd_ozon_customer_voice_detail.review_status_cn
            ),
            review_status = VALUES(review_status),
            rating = VALUES(rating),
            photos_amount = VALUES(photos_amount),
            videos_amount = VALUES(videos_amount),
            comments_amount = VALUES(comments_amount)
        """
    )

    async def upsert_from_ods(
        self, db: AsyncSession, *, shop_id: Optional[int] = None
    ) -> Dict[str, int]:
        source_query = (
            select(func.count())
            .select_from(ODSOzonReview)
            .where(ODSOzonReview.review_id.is_not(None))
        )
        if shop_id is not None:
            source_query = source_query.where(ODSOzonReview.shop_id == shop_id)
        source_count = int((await db.execute(source_query)).scalar_one())
        if source_count == 0:
            return {"source_count": 0, "affected_rows": 0}
        result = await db.execute(self._upsert_statement, {"shop_id": shop_id})
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
        published_from: Optional[datetime] = None,
        published_to: Optional[datetime] = None,
        offer_id: Optional[str] = None,
        sku: Optional[int] = None,
        rating: Optional[int] = None,
        order_status: Optional[str] = None,
        review_status: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Select[Any]:
        model = DWDOzonCustomerVoiceDetail
        if not allowed_shop_ids:
            return query.where(false())
        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if published_from is not None:
            query = query.where(model.published_at >= published_from)
        if published_to is not None:
            query = query.where(model.published_at < published_to)
        if offer_id:
            query = query.where(
                model.offer_id.contains(offer_id.strip(), autoescape=True)
            )
        if sku is not None:
            query = query.where(model.sku == sku)
        if rating is not None:
            query = query.where(model.rating == rating)
        if order_status:
            query = query.where(model.order_status == order_status)
        if review_status:
            query = query.where(model.review_status == review_status)
        if keyword:
            value = keyword.strip()
            query = query.where(
                or_(
                    model.product_name.contains(value, autoescape=True),
                    model.product_name_cn.contains(value, autoescape=True),
                    model.review_text.contains(value, autoescape=True),
                    model.review_text_cn.contains(value, autoescape=True),
                    model.order_status_cn.contains(value, autoescape=True),
                    model.review_status_cn.contains(value, autoescape=True),
                )
            )
        return query

    def _ordered(self, query: Select[Any], sort_order: str) -> Select[Any]:
        model = DWDOzonCustomerVoiceDetail
        date_order = (
            model.published_at.asc()
            if sort_order == "asc"
            else model.published_at.desc()
        )
        return query.order_by(date_order, model.shop_id.asc(), model.review_id.asc())

    async def list_items(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        sort_order: str,
        **filters: Any,
    ) -> tuple[list[DWDOzonCustomerVoiceDetail], int]:
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDOzonCustomerVoiceDetail), **filters
        )
        total = int((await db.execute(count_query)).scalar_one())
        query = self._ordered(
            self._apply_filters(select(DWDOzonCustomerVoiceDetail), **filters),
            sort_order,
        )
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await db.execute(query)).scalars().all()), total

    async def list_for_export(
        self, db: AsyncSession, *, sort_order: str, **filters: Any
    ) -> list[DWDOzonCustomerVoiceDetail]:
        query = self._ordered(
            self._apply_filters(select(DWDOzonCustomerVoiceDetail), **filters),
            sort_order,
        )
        return list((await db.execute(query)).scalars().all())

    async def list_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[OzonCustomerVoiceKey],
    ) -> list[DWDOzonCustomerVoiceDetail]:
        if not allowed_shop_ids or not keys:
            return []
        values = [(key.shop_id, key.review_id) for key in keys]
        model = DWDOzonCustomerVoiceDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.review_id).in_(values),
        )
        return list((await db.execute(self._ordered(query, "desc"))).scalars().all())


crud_dwd_ozon_customer_voice_detail = CRUDDWDOzonCustomerVoiceDetail()
