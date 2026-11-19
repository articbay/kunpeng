"""Ozon return listing and export service."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.ozon.return_detail import crud_dwd_ozon_return_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_return import (OzonReturnExportRequest,
                                         OzonReturnFilters, OzonReturnItem)
from kunpeng.services.ozon_return_status_translation import \
    resolve_ozon_return_status_cn
from kunpeng.services.wb_sales_funnel_service import build_xlsx
from kunpeng.utils.timezone import platform_tz

OZON_RETURN_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("模式", "schema"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("货件编号", "posting_number"),
    ("订单ID", "order_id"),
    ("订单编号", "order_number"),
    ("货号", "offer_id"),
    ("OZON SKU ID", "nm_id"),
    ("下订单日期", "order_date"),
    ("退货日期", "return_date"),
    ("退货状态", "status_display_name"),
    ("退货状态（中文）", "status_display_name_cn"),
    ("状态日期", "status_change_at"),
    ("赔偿状态", "compensation_status_display_name"),
    ("赔偿状态（中文）", "compensation_status_display_name_cn"),
    ("赔偿状态日期", "compensation_status_change_at"),
    ("退货原因", "return_reason_name"),
    ("退货原因（中文）", "return_reason_name_cn"),
    ("买家评论", "buyer_comment"),
    ("买家评论（中文）", "buyer_comment_cn"),
    ("退货数量", "quantity"),
    ("货件已打开", "is_opened"),
    ("目的地", "target_place_name"),
    ("目的地（中文）", "target_place_name_cn"),
    ("存储地址", "target_place_address"),
    ("存储地址（中文）", "target_place_address_cn"),
    ("转到“到达取货点”", "ready_to_pickup_at"),
    ("位置", "place_name"),
    ("位置（中文）", "place_name_cn"),
    ("向卖家退货日期", "picked_up_at"),
    ("存储天数", "storage_days"),
    ("免费存储的最后一天", "storage_expire_at"),
    ("退货条形码", "logistic_barcode"),
    ("仓储费用", "storage_fee_amount"),
    ("仓储费用币种", "storage_fee_currency"),
    ("销毁费用", "utilization_fee_amount"),
    ("销毁费用币种", "utilization_fee_currency"),
    ("商品价格", "price_amount"),
    ("商品价格币种", "price_currency"),
    ("佣金百分比", "commission_percent"),
    ("佣金", "commission_amount"),
    ("佣金币种", "commission_currency"),
    ("不含佣金的价格", "price_without_commission_amount"),
    ("不含佣金价格币种", "price_without_commission_currency"),
)

DATETIME_FIELDS = (
    "status_change_at",
    "compensation_status_change_at",
    "ready_to_pickup_at",
    "picked_up_at",
    "storage_expire_at",
    "utilization_forecast_at",
    "order_date",
    "return_date",
)


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local_value = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_bounds(
    filters: OzonReturnFilters,
) -> tuple[Optional[datetime], Optional[datetime]]:
    order_from = (
        _moscow_date_to_utc_naive(filters.date_from) if filters.date_from else None
    )
    order_to = (
        _moscow_date_to_utc_naive(filters.date_to + timedelta(days=1))
        if filters.date_to
        else None
    )
    return order_from, order_to


class OzonReturnService:
    """Coordinate authorization, Ozon DWD queries and Excel export."""

    @staticmethod
    def _build_item(record: object) -> OzonReturnItem:
        item = OzonReturnItem.model_validate(record)
        status_display_name_cn = resolve_ozon_return_status_cn(
            status_sys_name=item.status_sys_name,
            status_display_name=item.status_display_name,
            stored_translation=item.status_display_name_cn,
        )
        if status_display_name_cn == item.status_display_name_cn:
            return item
        return item.model_copy(
            update={"status_display_name_cn": status_display_name_cn}
        )

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    def _query_kwargs(
        self,
        filters: OzonReturnFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        order_from, order_to = _utc_bounds(filters)
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "order_from": order_from,
            "order_to": order_to,
            "return_id": filters.return_id,
            "nm_id": filters.nm_id,
            "posting_number": filters.posting_number,
            "order_id": filters.order_id,
            "order_number": filters.order_number,
            "offer_id": filters.offer_id,
            "brand_name": filters.brand_name,
            "category_name": filters.category_name,
            "product_name": filters.product_name,
            "status": filters.status,
            "return_type": filters.return_type,
            "schema": filters.schema,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_returns(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonReturnFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonReturnItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_ozon_return_detail.list_returns(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[OzonReturnItem](
            items=[self._build_item(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_returns(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: OzonReturnExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_ozon_return_detail.list_returns_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_ozon_return_detail.list_returns_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)

        rows = []
        for record in records:
            item = self._build_item(record)
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(row["shop_id"])
            for field in DATETIME_FIELDS:
                value = getattr(item, field)
                if value:
                    row[field] = value.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(OZON_RETURN_EXPORT_COLUMNS, rows, sheet_name="退货")


ozon_return_service = OzonReturnService()
