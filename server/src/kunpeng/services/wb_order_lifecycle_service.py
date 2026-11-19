"""Wildberries order lifecycle listing, summary and export."""

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwm.wildberries.order_lifecycle_query import (
    crud_dwm_wb_order_lifecycle_query,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order_lifecycle import (
    WBOrderLifecycleExportRequest,
    WBOrderLifecycleFilters,
    WBOrderLifecycleItem,
    WBOrderLifecycleSummary,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("SRID", "srid"),
    ("订单ID", "order_id"),
    ("购物车ID", "order_uid"),
    ("供货单ID", "supply_id"),
    ("WB商品ID", "nm_id"),
    ("卖家货号", "supplier_article"),
    ("条码", "barcode"),
    ("商品名称（中文）", "product_title_cn"),
    ("商品名称", "product_title"),
    ("下单时间", "order_at"),
    ("生命周期阶段", "lifecycle_stage_cn"),
    ("卖家状态", "supplier_status_cn"),
    ("卖家状态编码", "supplier_status"),
    ("WB状态", "wb_status_cn"),
    ("WB状态编码", "wb_status"),
    ("是否售出", "is_sold"),
    ("是否取消", "is_cancelled"),
    ("取消时间", "cancelled_at"),
    ("销售时间", "sale_at"),
    ("销售事件ID", "sale_id"),
    ("正向销售财务明细数", "finance_sale_row_cnt"),
    ("首次财务销售时间", "finance_first_sale_at"),
    ("退货记录数", "return_cnt"),
    ("最新退货状态", "latest_return_status_cn"),
    ("最新退货类型", "latest_return_type_cn"),
    ("最新退货原因", "latest_return_reason_cn"),
    ("退货关联方法", "return_link_method"),
    ("供货单名称", "supply_name"),
    ("供货单是否完成", "supply_is_done"),
    ("仓库", "warehouse_name_cn"),
    ("国家", "country_name_cn"),
    ("地区", "region_name_cn"),
    ("折后价格", "price_with_disc"),
    ("最终价格", "finished_price"),
    ("统计订单来源", "has_statistics_order_data"),
    ("Marketplace来源", "has_marketplace_order_data"),
    ("供货单来源", "has_supply_data"),
    ("销售接口来源", "has_sale_data"),
    ("财务来源", "has_finance_data"),
    ("退货来源", "has_return_data"),
    ("更新时间", "update_time"),
)


class WBOrderLifecycleService:
    async def _allowed(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db,
            user_id=user_id,
            platform="wildberries",
        )

    @staticmethod
    def _kwargs(filters: WBOrderLifecycleFilters, allowed: list[int]) -> dict:
        return {
            "allowed_shop_ids": allowed,
            **filters.model_dump(mode="python"),
        }

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBOrderLifecycleFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBOrderLifecycleItem]:
        allowed = await self._allowed(db, user_id)
        rows, total = await crud_dwm_wb_order_lifecycle_query.list_items(
            db,
            page=page,
            page_size=page_size,
            **self._kwargs(filters, allowed),
        )
        return PageResponse[WBOrderLifecycleItem](
            items=[WBOrderLifecycleItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def summary(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBOrderLifecycleFilters,
    ) -> WBOrderLifecycleSummary:
        allowed = await self._allowed(db, user_id)
        result = await crud_dwm_wb_order_lifecycle_query.get_summary(
            db,
            **self._kwargs(filters, allowed),
        )
        return WBOrderLifecycleSummary.model_validate(result)

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: WBOrderLifecycleExportRequest,
    ) -> bytes:
        allowed = await self._allowed(db, user_id)
        if request.scope == "selected":
            rows = await crud_dwm_wb_order_lifecycle_query.list_by_keys(
                db,
                allowed_shop_ids=allowed,
                keys=request.selected_keys,
            )
        else:
            rows = await crud_dwm_wb_order_lifecycle_query.list_for_export(
                db,
                **self._kwargs(request.filters, allowed),
            )
        data = [
            WBOrderLifecycleItem.model_validate(row).model_dump(mode="python")
            for row in rows
        ]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for row in data:
            row["shop_name"] = shop_names.get(row["shop_id"])
        return build_xlsx(EXPORT_COLUMNS, data, sheet_name="WB订单生命周期")


wb_order_lifecycle_service = WBOrderLifecycleService()
