"""Build and query the Wildberries VOC question DWD table."""

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import Select, and_, false, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.voc_question import DWDWBVOCQuestionDetail
from kunpeng.models.ods.wildberries.feedbacks import ODSWBQuestion
from kunpeng.schemas.wb_voc_question import AnswerStatus, WBVOCQuestionKey


class CRUDDWDWBVOCQuestionDetail:
    """Idempotently reconcile customer question details from ODS."""

    _upsert_statement = text(
        """
        INSERT INTO dwd_wb_voc_question_detail (
            shop_id,
            question_id,
            created_date,
            supplier_article,
            nm_id,
            brand_name,
            text,
            answer
        )
        SELECT
            source_shop_id,
            source_question_id,
            source_created_date,
            source_supplier_article,
            source_nm_id,
            source_brand_name,
            source_text,
            source_answer
        FROM (
            SELECT
                shop_id AS source_shop_id,
                question_id AS source_question_id,
                created_date AS source_created_date,
                supplier_article AS source_supplier_article,
                nm_id AS source_nm_id,
                brand_name AS source_brand_name,
                text AS source_text,
                JSON_UNQUOTE(JSON_EXTRACT(answer, '$.text')) AS source_answer
            FROM ods_wb_questions
            WHERE (:shop_id IS NULL OR shop_id = :shop_id)
        ) AS source_rows
        ON DUPLICATE KEY UPDATE
            created_date = source_created_date,
            supplier_article = source_supplier_article,
            nm_id = source_nm_id,
            brand_name = source_brand_name,
            text_cn = IF(NOT (text <=> source_text), NULL, text_cn),
            text = source_text,
            answer_cn = IF(NOT (answer <=> source_answer), NULL, answer_cn),
            answer = source_answer
        """
    )

    async def upsert_from_ods(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert new questions and refresh existing DWD rows."""
        source_count = select(func.count()).select_from(ODSWBQuestion)
        if shop_id is not None:
            source_count = source_count.where(ODSWBQuestion.shop_id == shop_id)

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
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
    ) -> Select[Any]:
        model = DWDWBVOCQuestionDetail
        if not allowed_shop_ids:
            return query.where(false())

        query = query.where(model.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(model.shop_id == shop_id)
        if created_from is not None:
            query = query.where(model.created_date >= created_from)
        if created_to is not None:
            query = query.where(model.created_date < created_to)
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
                    model.answer.contains(normalized_keyword, autoescape=True),
                    model.answer_cn.contains(normalized_keyword, autoescape=True),
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
        model = DWDWBVOCQuestionDetail
        created_order = (
            model.created_date.asc()
            if sort_order == "asc"
            else model.created_date.desc()
        )
        return query.order_by(
            created_order, model.shop_id.asc(), model.question_id.asc()
        )

    async def list_questions(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        page: int,
        page_size: int,
        shop_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
        sort_order: str = "desc",
    ) -> tuple[list[DWDWBVOCQuestionDetail], int]:
        """Return one stable page and the filtered row count."""
        filter_args = {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": shop_id,
            "created_from": created_from,
            "created_to": created_to,
            "supplier_article": supplier_article,
            "nm_id": nm_id,
            "brand_name": brand_name,
            "keyword": keyword,
            "answer_status": answer_status,
        }
        count_query = self._apply_filters(
            select(func.count()).select_from(DWDWBVOCQuestionDetail),
            **filter_args,
        )
        total = int((await db.execute(count_query)).scalar_one())

        data_query = self._apply_filters(select(DWDWBVOCQuestionDetail), **filter_args)
        data_query = (
            self._ordered_query(data_query, sort_order=sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list((await db.execute(data_query)).scalars().all())
        return records, total

    async def list_questions_for_export(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        shop_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        supplier_article: Optional[str] = None,
        nm_id: Optional[int] = None,
        brand_name: Optional[str] = None,
        keyword: Optional[str] = None,
        answer_status: Optional[AnswerStatus] = None,
        sort_order: str = "desc",
    ) -> list[DWDWBVOCQuestionDetail]:
        """Return all filtered rows for server-side Excel export."""
        query = self._apply_filters(
            select(DWDWBVOCQuestionDetail),
            allowed_shop_ids=allowed_shop_ids,
            shop_id=shop_id,
            created_from=created_from,
            created_to=created_to,
            supplier_article=supplier_article,
            nm_id=nm_id,
            brand_name=brand_name,
            keyword=keyword,
            answer_status=answer_status,
        )
        query = self._ordered_query(query, sort_order=sort_order)
        return list((await db.execute(query)).scalars().all())

    async def list_questions_by_keys(
        self,
        db: AsyncSession,
        *,
        allowed_shop_ids: Sequence[int],
        keys: Sequence[WBVOCQuestionKey],
    ) -> list[DWDWBVOCQuestionDetail]:
        """Return selected rows while enforcing the caller's shop scope."""
        if not allowed_shop_ids or not keys:
            return []
        composite_keys = [(key.shop_id, key.question_id) for key in keys]
        model = DWDWBVOCQuestionDetail
        query = select(model).where(
            model.shop_id.in_(allowed_shop_ids),
            tuple_(model.shop_id, model.question_id).in_(composite_keys),
        )
        query = self._ordered_query(query, sort_order="desc")
        return list((await db.execute(query)).scalars().all())


crud_dwd_wb_voc_question_detail = CRUDDWDWBVOCQuestionDetail()
