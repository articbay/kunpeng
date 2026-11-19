"""Build and query the Wildberries VOC feedback DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, and_, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.voc_feedback import DWDWBVOCFeedbackDetail
from kunpeng.models.ods.wildberries.feedbacks import ODSWBFeedback
from kunpeng.schemas.wb_voc_feedback import AnswerStatus, WBVOCFeedbackKey


class CRUDDWDWBVOCFeedbackDetail:
    """Idempotently reconcile customer feedback details from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_wb_voc_feedback_detail (
            shop_id,
            feedback_id,
            created_date,
            supplier_article,
            nm_id,
            product_name,
            product_valuation,
            brand_name,
            text,
            pros,
            cons,
            user_name,
            color,
            size,
            answer,
            parent_feedback_id,
            child_feedback_id
        )
        SELECT
            source_shop_id,
            source_feedback_id,
            source_created_date,
            source_supplier_article,
            source_nm_id,
            source_product_name,
            source_product_valuation,
            source_brand_name,
            source_text,
            source_pros,
            source_cons,
            source_user_name,
            source_color,
            source_size,
            source_answer,
            source_parent_feedback_id,
            source_child_feedback_id
        FROM (
            SELECT
                shop_id AS source_shop_id,
                feedback_id AS source_feedback_id,
                created_date AS source_created_date,
                supplier_article AS source_supplier_article,
                nm_id AS source_nm_id,
                product_name AS source_product_name,
                product_valuation AS source_product_valuation,
                brand_name AS source_brand_name,
                text AS source_text,
                pros AS source_pros,
                cons AS source_cons,
                user_name AS source_user_name,
                color AS source_color,
                size AS source_size,
                JSON_UNQUOTE(JSON_EXTRACT(answer, '$.text')) AS source_answer,
                parent_feedback_id AS source_parent_feedback_id,
                child_feedback_id AS source_child_feedback_id
            FROM ods_wb_feedbacks
            WHERE (:shop_id IS NULL OR shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            created_date = source_created_date,
            supplier_article = source_supplier_article,
            nm_id = source_nm_id,
            product_name_cn = IF(
                NOT (product_name <=> source_product_name),
                NULL,
                product_name_cn
            ),
            product_name = source_product_name,
            product_valuation = source_product_valuation,
            brand_name = source_brand_name,
            text_cn = IF(NOT (text <=> source_text), NULL, text_cn),
            text = source_text,
            pros_cn = IF(NOT (pros <=> source_pros), NULL, pros_cn),
            pros = source_pros,
            cons_cn = IF(NOT (cons <=> source_cons), NULL, cons_cn),
            cons = source_cons,
            user_name = source_user_name,
            color_cn = IF(NOT (color <=> source_color), NULL, color_cn),
            color = source_color,
            size_cn = IF(NOT (size <=> source_size), NULL, size_cn),
            size = source_size,
            answer_cn = IF(NOT (answer <=> source_answer), NULL, answer_cn),
            answer = source_answer,
            parent_feedback_id = source_parent_feedback_id,
            child_feedback_id = source_child_feedback_id
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new feedbacks and refresh existing DWD rows."""
        source_count = select(func.count()).select_from(ODSWBFeedback)
        if shop_id is not None:
            source_count = source_count.where(ODSWBFeedback.shop_id == shop_id)

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
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        product_valuations: Sequence[int] = (),
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
    ) -> Select[Any]:
        model = DWDWBVOCFeedbackDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if created_from is not None:
            query = query.where(model.created_date >= created_from)
        if created_to is not None:
            query = query.where(model.created_date < created_to)
        if product_valuations:
            query = query.where(model.product_valuation.in_(product_valuations))
        if supplier_article:
            query = query.where(
                model.supplier_article.contains(
                    supplier_article.strip(), autoescape=True
                )
            )
        if nm_id is not None:
            query = query.where(model.nm_id == nm_id)
        if brand_name:
            query = query.where(
                model.brand_name.contains(brand_name.strip(), autoescape=True)
            )
        if keyword:
            normalized_keyword = keyword.strip()
            query = query.where(
                or_(
                    model.text.contains(normalized_keyword, autoescape=True),
                    model.text_cn.contains(normalized_keyword, autoescape=True),
                    model.pros.contains(normalized_keyword, autoescape=True),
                    model.pros_cn.contains(normalized_keyword, autoescape=True),
                    model.cons.contains(normalized_keyword, autoescape=True),
                    model.cons_cn.contains(normalized_keyword, autoescape=True),
                    model.user_name.contains(normalized_keyword, autoescape=True),
                    model.color_cn.contains(normalized_keyword, autoescape=True),
                    model.size_cn.contains(normalized_keyword, autoescape=True),
                    model.answer.contains(normalized_keyword, autoescape=True),
                    model.answer_cn.contains(normalized_keyword, autoescape=True),
                    model.product_name.contains(normalized_keyword, autoescape=True),
                    model.product_name_cn.contains(normalized_keyword, autoescape=True),
                )
            )
        if answer_status == "answered":
            query = query.where(
                and_(model.answer.is_not(None), func.trim(model.answer) != "")
            )
        elif answer_status == "unanswered":
            query = query.where(
                or_(model.answer.is_(None), func.trim(model.answer) == "")
            )
        return query

    def _ordered_query(self, query: Select[Any], *, sort_order: str) -> Select[Any]:
        model = DWDWBVOCFeedbackDetail
        created_order = (
            model.created_date.asc()
            if sort_order == "asc"
            else model.created_date.desc()
        )
        return query.order_by(
            created_order, model.shop_id.asc(), model.feedback_id.asc()
        )

    async def list_feedbacks(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        page: int,
        page_size: int,
        shop_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        product_valuations: Sequence[int] = (),
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
        sort_order: str = "desc",
    ) -> tuple[list[DWDWBVOCFeedbackDetail], int]:
        """Return one stable page and the filtered row count."""
        filter_args = {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": shop_id,
            "created_from": created_from,
            "created_to": created_to,
            "product_valuations": product_valuations,
            "supplier_article": supplier_article,
            "nm_id": nm_id,
            "brand_name": brand_name,
            "keyword": keyword,
            "answer_status": answer_status,
        }
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDWBVOCFeedbackDetail),
            **filter_args,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(select(DWDWBVOCFeedbackDetail), **filter_args)
        data_query = (
            self._ordered_query(data_query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list((await db.execute(data_query)).scalars().all())
        return records, total

    async def list_feedbacks_for_export(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        product_valuations: Sequence[int] = (),
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
        sort_order: str = "desc",
    ) -> list[DWDWBVOCFeedbackDetail]:
        """Return all filtered rows for server-side Excel export."""
        query = self._apply_filters(
            select(DWDWBVOCFeedbackDetail),
            allowed_shop_ids=allowed_shop_ids,
            shop_id=shop_id,
            created_from=created_from,
            created_to=created_to,
            product_valuations=product_valuations,
            supplier_article=supplier_article,
            nm_id=nm_id,
            brand_name=brand_name,
            keyword=keyword,
            answer_status=answer_status,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_feedbacks_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBVOCFeedbackKey],
    ) -> list[DWDWBVOCFeedbackDetail]:
        """Return selected rows while enforcing the caller's shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.feedback_id) for key in keys]
        model = DWDWBVOCFeedbackDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.feedback_id).in_(composite_keys),
        )
        query = self._ordered_query(query, sort_order="desc")
        return list((await db.execute(query)).scalars().all())


crud_dwd_wb_voc_feedback_detail = CRUDDWDWBVOCFeedbackDetail()
