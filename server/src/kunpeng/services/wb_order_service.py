"""Wildberries order listing and export service."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.order_detail import crud_dwd_wb_order_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order import WBOrderExportRequest, WBOrderFilters, WBOrderItem
from kunpeng.services.wb_order_status_translation import (
    resolve_wb_order_status_cn,
    resolve_wb_supplier_status_cn,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx
from kunpeng.utils.timezone import platform_tz

ORDER_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("订单ID（工作编号）", "order_id"),
    ("供货ID", "supply_id"),
    ("贴纸ID", "sticker_id"),
    ("订单创建时间（莫斯科）", "order_dt"),
    ("商品名称", "title"),
    ("商品名称（中文）", "title_cn"),
    ("尺寸", "tech_size"),
    ("尺寸（中文）", "tech_size_cn"),
    ("颜色", "color"),
    ("颜色（中文）", "color_cn"),
    ("原生条形码", "barcode_ori"),
    ("手调条形码", "barcode_hand"),
    ("零售价", "retail_price"),
    ("币种", "currency"),
    ("WB商品ID", "nm_id"),
    ("卖家货号", "supplier_article"),
    ("卖家仓库ID", "warehouse_id"),
    ("卖家仓库", "warehouse_name"),
    ("卖家仓库（中文）", "warehouse_name_cn"),
    ("WB状态", "wb_status"),
    ("WB状态（中文）", "wb_status_cn"),
    ("地址", "address"),
    ("地址（中文）", "address_cn"),
    ("是否B2B", "is_b2b"),
    ("配送类型", "delivery_type"),
    ("卖家处理状态", "supplier_status"),
    ("卖家处理状态（中文）", "supplier_status_cn"),
    ("是否可取消", "is_cancellable"),
    ("订单价格", "order_price"),
    ("币种", "currency_name"),
    ("配送办公点ID", "office_id"),
    ("货物类型", "cargo_type"),
    ("跨境类型", "cross_border_type"),
    ("是否零订单", "is_zero_order"),
)


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local_value = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_bounds(
    filters: WBOrderFilters,
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


class WBOrderService:
    """Coordinate authorization, DWD queries, timezone handling and export."""

    @staticmethod
    def _build_item(record: object) -> WBOrderItem:
        item = WBOrderItem.model_validate(record)
        wb_status_cn = resolve_wb_order_status_cn(
            status=item.wb_status,
            stored_translation=item.wb_status_cn,
        )
        supplier_status_cn = resolve_wb_supplier_status_cn(
            status=item.supplier_status,
            stored_translation=item.supplier_status_cn,
        )
        order_price = (
            item.converted_price / Decimal("100")
            if item.converted_price is not None
            else None
        )
        currency_name = (
            "人民币"
            if item.converted_currency_code == 156
            else (
                str(item.converted_currency_code)
                if item.converted_currency_code is not None
                else None
            )
        )
        updates = {
            "order_price": order_price,
            "currency_name": currency_name,
        }
        if wb_status_cn != item.wb_status_cn:
            updates["wb_status_cn"] = wb_status_cn
        if supplier_status_cn != item.supplier_status_cn:
            updates["supplier_status_cn"] = supplier_status_cn
        return item.model_copy(update=updates)

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    def _query_kwargs(
        self,
        filters: WBOrderFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        order_from, order_to = _utc_bounds(filters)
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "order_from": order_from,
            "order_to": order_to,
            "order_id": filters.order_id,
            "supply_id": filters.supply_id,
            "sticker_id": filters.sticker_id,
            "nm_id": filters.nm_id,
            "supplier_article": filters.supplier_article,
            "warehouse_id": filters.warehouse_id,
            "wb_status": filters.wb_status,
            "supplier_status": filters.supplier_status,
            "delivery_type": filters.delivery_type,
            "is_cancellable": filters.is_cancellable,
            "is_b2b": filters.is_b2b,
            "is_zero_order": filters.is_zero_order,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBOrderFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBOrderItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_wb_order_detail.list_orders(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[WBOrderItem](
            items=[self._build_item(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBOrderExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_wb_order_detail.list_orders_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_wb_order_detail.list_orders_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        items = [self._build_item(record) for record in records]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)
        rows = []
        for item in items:
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            if item.order_dt:
                row["order_dt"] = item.order_dt.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(ORDER_EXPORT_COLUMNS, rows, sheet_name="WB履约订单")


wb_order_service = WBOrderService()
