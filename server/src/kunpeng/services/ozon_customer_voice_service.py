"""Ozon customer voice listing, translation and Excel export service."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.ozon.customer_voice import crud_dwd_ozon_customer_voice_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_customer_voice import (
    OzonCustomerVoiceExportRequest,
    OzonCustomerVoiceFilters,
    OzonCustomerVoiceItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx
from kunpeng.utils.timezone import platform_tz

OZON_CUSTOMER_VOICE_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("月份", "month"),
    ("货号", "offer_id"),
    ("SKU", "sku"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("订单号", "posting_number"),
    ("收货状态", "order_status"),
    ("收货状态（中文）", "order_status_cn"),
    ("检讨文本", "review_text"),
    ("检讨文本（中文）", "review_text_cn"),
    ("发布日期", "published_at"),
    ("评价状态", "review_status"),
    ("评价状态（中文）", "review_status_cn"),
    ("评分", "rating"),
    ("照片数量", "photos_amount"),
    ("视频数量", "videos_amount"),
    ("对检讨的回应数目", "comments_amount"),
)


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local.astimezone(timezone.utc).replace(tzinfo=None)


class OzonCustomerVoiceService:
    async def _allowed_shop_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    def _query_kwargs(
        self, filters: OzonCustomerVoiceFilters, allowed_shop_ids: list[int]
    ) -> dict:
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "published_from": (
                _moscow_date_to_utc_naive(filters.date_from)
                if filters.date_from
                else None
            ),
            "published_to": (
                _moscow_date_to_utc_naive(filters.date_to + timedelta(days=1))
                if filters.date_to
                else None
            ),
            "offer_id": filters.offer_id,
            "sku": filters.sku,
            "rating": filters.rating,
            "order_status": filters.order_status,
            "review_status": filters.review_status,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonCustomerVoiceFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonCustomerVoiceItem]:
        allowed = await self._allowed_shop_ids(db, user_id)
        rows, total = await crud_dwd_ozon_customer_voice_detail.list_items(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed),
        )
        return PageResponse[OzonCustomerVoiceItem](
            items=[OzonCustomerVoiceItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: OzonCustomerVoiceExportRequest,
    ) -> bytes:
        allowed = await self._allowed_shop_ids(db, user_id)
        if request.scope == "selected":
            records = await crud_dwd_ozon_customer_voice_detail.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            records = await crud_dwd_ozon_customer_voice_detail.list_for_export(
                db, **self._query_kwargs(request.filters, allowed)
            )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        rows = []
        for record in records:
            item = OzonCustomerVoiceItem.model_validate(record)
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            if item.published_at:
                row["published_at"] = item.published_at.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(
            OZON_CUSTOMER_VOICE_EXPORT_COLUMNS, rows, sheet_name="Ozon客户声音"
        )


ozon_customer_voice_service = OzonCustomerVoiceService()
