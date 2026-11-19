"""Wildberries customer question listing and export service."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.voc_question import crud_dwd_wb_voc_question_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_voc_question import (
    WBVOCQuestionExportRequest,
    WBVOCQuestionFilters,
    WBVOCQuestionItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx
from kunpeng.utils.timezone import platform_tz

QUESTION_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("提问ID", "question_id"),
    ("提问时间（莫斯科）", "created_date"),
    ("卖家货号", "supplier_article"),
    ("WB商品ID", "nm_id"),
    ("品牌", "brand_name"),
    ("提问正文", "text"),
    ("提问正文（中文）", "text_cn"),
    ("商家回复", "answer"),
    ("商家回复（中文）", "answer_cn"),
)


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local_value = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_bounds(
    filters: WBVOCQuestionFilters,
) -> tuple[Optional[datetime], Optional[datetime]]:
    created_from = (
        _moscow_date_to_utc_naive(filters.date_from) if filters.date_from else None
    )
    created_to = (
        _moscow_date_to_utc_naive(filters.date_to + timedelta(days=1))
        if filters.date_to
        else None
    )
    return created_from, created_to


class WBVOCQuestionService:
    """Coordinate authorization, DWD queries, timezone handling and export."""

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    def _query_kwargs(
        self,
        filters: WBVOCQuestionFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        created_from, created_to = _utc_bounds(filters)
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "created_from": created_from,
            "created_to": created_to,
            "supplier_article": filters.supplier_article,
            "nm_id": filters.nm_id,
            "brand_name": filters.brand_name,
            "keyword": filters.keyword,
            "answer_status": filters.answer_status,
            "sort_order": filters.sort_order,
        }

    async def list_questions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBVOCQuestionFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBVOCQuestionItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_wb_voc_question_detail.list_questions(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[WBVOCQuestionItem](
            items=[WBVOCQuestionItem.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_questions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBVOCQuestionExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_wb_voc_question_detail.list_questions_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_wb_voc_question_detail.list_questions_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        items = [WBVOCQuestionItem.model_validate(record) for record in records]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)
        rows = []
        for item in items:
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            if item.created_date:
                row["created_date"] = item.created_date.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(QUESTION_EXPORT_COLUMNS, rows, sheet_name="WB客户提问")


wb_voc_question_service = WBVOCQuestionService()
