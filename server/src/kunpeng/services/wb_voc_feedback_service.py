"""Wildberries customer feedback listing and export service."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.voc_feedback import crud_dwd_wb_voc_feedback_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_voc_feedback import (
    WBVOCFeedbackExportRequest,
    WBVOCFeedbackFilters,
    WBVOCFeedbackItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx
from kunpeng.utils.timezone import platform_tz

FEEDBACK_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("评价ID", "feedback_id"),
    ("评价时间（莫斯科）", "created_date"),
    ("卖家货号", "supplier_article"),
    ("WB商品ID", "nm_id"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("星级", "product_valuation"),
    ("品牌", "brand_name"),
    ("评价正文", "text"),
    ("评价正文（中文）", "text_cn"),
    ("优点", "pros"),
    ("优点（中文）", "pros_cn"),
    ("缺点", "cons"),
    ("缺点（中文）", "cons_cn"),
    ("用户姓名", "user_name"),
    ("颜色", "color"),
    ("颜色（中文）", "color_cn"),
    ("尺码", "size"),
    ("尺码（中文）", "size_cn"),
    ("商家回复", "answer"),
    ("商家回复（中文）", "answer_cn"),
    ("初始评价ID", "parent_feedback_id"),
    ("追加评价ID", "child_feedback_id"),
)


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local_value = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_bounds(
    filters: WBVOCFeedbackFilters,
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


class WBVOCFeedbackService:
    """Coordinate authorization, DWD queries, timezone handling and export."""

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    def _query_kwargs(
        self,
        filters: WBVOCFeedbackFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        created_from, created_to = _utc_bounds(filters)
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "created_from": created_from,
            "created_to": created_to,
            "product_valuations": filters.product_valuations,
            "supplier_article": filters.supplier_article,
            "nm_id": filters.nm_id,
            "brand_name": filters.brand_name,
            "keyword": filters.keyword,
            "answer_status": filters.answer_status,
            "sort_order": filters.sort_order,
        }

    async def list_feedbacks(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBVOCFeedbackFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBVOCFeedbackItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_wb_voc_feedback_detail.list_feedbacks(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[WBVOCFeedbackItem](
            items=[WBVOCFeedbackItem.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_feedbacks(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBVOCFeedbackExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_wb_voc_feedback_detail.list_feedbacks_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_wb_voc_feedback_detail.list_feedbacks_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        items = [WBVOCFeedbackItem.model_validate(record) for record in records]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)
        rows = []
        for item in items:
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            if item.created_date:
                row["created_date"] = item.created_date.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(FEEDBACK_EXPORT_COLUMNS, rows, sheet_name="WB客户评价")


wb_voc_feedback_service = WBVOCFeedbackService()
