"""Ozon order lifecycle listing, summary and export."""

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwm.ozon.order_lifecycle_query import (
    crud_dwm_ozon_order_lifecycle_query,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_order_lifecycle import (
    OzonOrderLifecycleExportRequest,
    OzonOrderLifecycleFilters,
    OzonOrderLifecycleItem,
    OzonOrderLifecycleSummary,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("履约方式", "fulfillment_type"),
    ("发货号码", "posting_number"),
    ("Ozon SKU", "sku"),
    ("订单ID", "order_id"),
    ("订单号", "order_number"),
    ("卖家货号", "offer_id"),
    ("商品名称（中文）", "product_name_cn"),
    ("商品名称", "product_name"),
    ("下单数量", "quantity"),
    ("当前状态编码", "status_code"),
    ("当前子状态编码", "substatus_code"),
    ("当前状态", "status_name_cn"),
    ("进入处理时间", "in_process_at"),
    ("实际发货时间", "shipment_date"),
    ("移交配送时间", "transferred_to_delivery_at"),
    ("配送节点日期（非签收）", "delivery_date"),
    ("承诺送达时间", "promised_delivery_at"),
    ("取消时间", "cancellation_at"),
    ("退货记录数", "return_cnt"),
    ("累计退货数量", "return_qty"),
    ("首次退货日期", "first_return_date"),
    ("最新退货ID", "latest_return_id"),
    ("最新退货状态编码", "latest_return_status_sys_name"),
    ("最新退货状态", "latest_return_status_display_name_cn"),
    ("最新退货状态变更时间", "latest_return_status_change_at"),
    ("最新退货原因", "latest_return_reason_name_cn"),
    ("最近到达取货点时间", "last_ready_to_pickup_at"),
    ("最近向卖家退回时间", "last_picked_up_at"),
    ("创建时间", "create_time"),
    ("更新时间", "update_time"),
)


class OzonOrderLifecycleService:
    async def _allowed(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    @staticmethod
    def _kwargs(filters: OzonOrderLifecycleFilters, allowed: list[int]) -> dict:
        return {"allowed_shop_ids": allowed, **filters.model_dump(mode="python")}

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonOrderLifecycleFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonOrderLifecycleItem]:
        allowed = await self._allowed(db, user_id)
        rows, total = await crud_dwm_ozon_order_lifecycle_query.list_items(
            db, page=page, page_size=page_size, **self._kwargs(filters, allowed)
        )
        return PageResponse[OzonOrderLifecycleItem](
            items=[OzonOrderLifecycleItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def summary(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonOrderLifecycleFilters,
    ) -> OzonOrderLifecycleSummary:
        allowed = await self._allowed(db, user_id)
        result = await crud_dwm_ozon_order_lifecycle_query.get_summary(
            db, **self._kwargs(filters, allowed)
        )
        return OzonOrderLifecycleSummary.model_validate(result)

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: OzonOrderLifecycleExportRequest,
    ) -> bytes:
        allowed = await self._allowed(db, user_id)
        if request.scope == "selected":
            rows = await crud_dwm_ozon_order_lifecycle_query.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            rows = await crud_dwm_ozon_order_lifecycle_query.list_for_export(
                db, **self._kwargs(request.filters, allowed)
            )
        data = [
            OzonOrderLifecycleItem.model_validate(row).model_dump(mode="python")
            for row in rows
        ]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for row in data:
            row["shop_name"] = shop_names.get(row["shop_id"])
        return build_xlsx(EXPORT_COLUMNS, data, sheet_name="Ozon订单生命周期")


ozon_order_lifecycle_service = OzonOrderLifecycleService()
