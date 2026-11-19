"""Ozon sales-funnel listing and Excel export service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.ozon.sales_funnel import crud_dwd_ozon_sales_funnel_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_sales_funnel import (
    OzonSalesFunnelExportRequest,
    OzonSalesFunnelFilters,
    OzonSalesFunnelItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

OZON_SALES_FUNNEL_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("卖家商品编号", "offer_id"),
    ("Ozon SKU", "sku"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("商品品类", "category_name"),
    ("商品品类（中文）", "category_name_cn"),
    ("统计日期", "stat_date"),
    ("搜索和类目展示次数", "hits_view_search"),
    ("商品详情页浏览次数", "hits_view_pdp"),
    ("总展示/浏览次数", "hits_view"),
    ("搜索和类目访问用户数", "session_view_search"),
    ("商品详情页访问用户数", "session_view_pdp"),
    ("总访问用户数", "session_view"),
    ("搜索和类目加购次数", "hits_tocart_search"),
    ("商品详情页加购次数", "hits_tocart_pdp"),
    ("总加购次数", "hits_tocart"),
    ("搜索和类目加购转化率（%）", "conv_tocart_search"),
    ("商品详情页加购转化率（%）", "conv_tocart_pdp"),
    ("总加购转化率（%）", "conv_tocart"),
    ("下单商品件数", "ordered_units"),
    ("下单金额（₽）", "revenue"),
    ("送达商品件数", "delivered_units"),
    ("取消商品件数", "cancellations"),
    ("退货商品件数", "returns"),
    ("搜索和类目平均位置", "position_category"),
    ("加购至下单转化率（项目计算，%）", "cart_to_order_rate"),
)


class OzonSalesFunnelService:
    async def _allowed_shop_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    def _query_kwargs(
        self, filters: OzonSalesFunnelFilters, allowed_shop_ids: list[int]
    ) -> dict:
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "sku": filters.sku,
            "offer_id": filters.offer_id,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    def _item_dict(self, record: object, *, shop_names: dict[int, str]) -> dict:
        item = OzonSalesFunnelItem.model_validate(record)
        row = item.model_dump(mode="python")
        row["shop_name"] = shop_names.get(item.shop_id)
        row["stat_date"] = item.stat_date.strftime("%Y-%m-%d")
        return row

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonSalesFunnelFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonSalesFunnelItem]:
        allowed = await self._allowed_shop_ids(db, user_id)
        rows, total = await crud_dwd_ozon_sales_funnel_detail.list_items(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed),
        )
        return PageResponse[OzonSalesFunnelItem](
            items=[OzonSalesFunnelItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: OzonSalesFunnelExportRequest,
    ) -> bytes:
        allowed = await self._allowed_shop_ids(db, user_id)
        if request.scope == "selected":
            records = await crud_dwd_ozon_sales_funnel_detail.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            records = await crud_dwd_ozon_sales_funnel_detail.list_for_export(
                db, **self._query_kwargs(request.filters, allowed)
            )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        return build_xlsx(
            OZON_SALES_FUNNEL_EXPORT_COLUMNS,
            [self._item_dict(record, shop_names=shop_names) for record in records],
            sheet_name="Ozon销售漏斗",
        )


ozon_sales_funnel_service = OzonSalesFunnelService()
