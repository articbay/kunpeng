"""Wildberries statistics-order listing and export service."""

from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.order_statistics_detail import (
    crud_dwd_wb_order_statistics_detail,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order_statistics import (
    WBOrderStatisticsExportRequest,
    WBOrderStatisticsFilters,
    WBOrderStatisticsItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

ORDER_STATISTICS_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("系统订单号", "srid"),
    ("下单时间（莫斯科）", "order_date"),
    ("最后修改时间（莫斯科）", "last_change_date"),
    ("仓库名称", "warehouse_name"),
    ("仓库名称（中文）", "warehouse_name_cn"),
    ("国家", "country_name"),
    ("国家（中文）", "country_name_cn"),
    ("联邦管区", "oblast_okrug_name"),
    ("联邦管区（中文）", "oblast_okrug_name_cn"),
    ("地区", "region_name"),
    ("地区（中文）", "region_name_cn"),
    ("卖家货号", "supplier_article"),
    ("WB商品ID", "nm_id"),
    ("原生条形码", "barcode_ori"),
    ("手调条形码", "barcode_hand"),
    ("商品分类", "category"),
    ("商品分类（中文）", "category_cn"),
    ("商品品类", "subject_name"),
    ("商品品类（中文）", "subject_name_cn"),
    ("尺码", "tech_size"),
    ("尺码（中文）", "tech_size_cn"),
    ("原价", "total_price"),
    ("折扣百分比", "discount_percent"),
    ("折后价格", "price_with_disc"),
    ("最终价格", "finished_price"),
    ("是否取消", "is_cancel"),
    ("取消时间（莫斯科）", "cancel_date"),
    ("贴纸ID", "sticker_id"),
    ("订单组号", "g_number"),
)


def _local_bounds(
    filters: WBOrderStatisticsFilters,
) -> tuple[Optional[datetime], Optional[datetime]]:
    order_from = (
        datetime.combine(filters.date_from, time.min) if filters.date_from else None
    )
    order_to = (
        datetime.combine(filters.date_to + timedelta(days=1), time.min)
        if filters.date_to
        else None
    )
    return order_from, order_to


class WBOrderStatisticsService:
    """Coordinate permissions, local Moscow times and Excel export."""

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    def _query_kwargs(
        self,
        filters: WBOrderStatisticsFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        order_from, order_to = _local_bounds(filters)
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "order_from": order_from,
            "order_to": order_to,
            "srid": filters.srid,
            "warehouse_name": filters.warehouse_name,
            "country_name": filters.country_name,
            "oblast_okrug_name": filters.oblast_okrug_name,
            "region_name": filters.region_name,
            "supplier_article": filters.supplier_article,
            "nm_id": filters.nm_id,
            "category": filters.category,
            "subject_name": filters.subject_name,
            "is_cancel": filters.is_cancel,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBOrderStatisticsFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBOrderStatisticsItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_wb_order_statistics_detail.list_orders(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[WBOrderStatisticsItem](
            items=[WBOrderStatisticsItem.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBOrderStatisticsExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_wb_order_statistics_detail.list_orders_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_wb_order_statistics_detail.list_orders_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        items = [WBOrderStatisticsItem.model_validate(record) for record in records]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)
        rows = []
        datetime_fields = (
            "order_date",
            "last_change_date",
            "cancel_date",
        )
        for item in items:
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            for field in datetime_fields:
                value = getattr(item, field)
                if value:
                    row[field] = value.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
        return build_xlsx(
            ORDER_STATISTICS_EXPORT_COLUMNS,
            rows,
            sheet_name="WB统计订单",
        )


wb_order_statistics_service = WBOrderStatisticsService()
