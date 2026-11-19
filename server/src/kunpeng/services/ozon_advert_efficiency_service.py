"""Ozon advertising efficiency listing and Excel export service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.ozon.advert_efficiency import (
    crud_dwd_ozon_advert_efficiency_detail,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_advert_efficiency import (
    OzonAdvertEfficiencyExportRequest,
    OzonAdvertEfficiencyFilters,
    OzonAdvertEfficiencyItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("统计日期", "stat_date"),
    ("SKU", "sku"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("品类名称", "category_name"),
    ("品类名称（中文）", "category_name_cn"),
    ("工具", "payment_type"),
    ("投放位置", "placement"),
    ("广告活动 ID", "campaign_id"),
    ("广告活动名称", "campaign_name"),
    ("费用，₽", "money_spent"),
    ("广告费用份额, %", "drr"),
    ("销售额，₽", "orders_money"),
    ("订单，个", "orders"),
    ("CTR, %", "ctr"),
    ("展现量", "views"),
    ("点击次数", "clicks"),
    ("添加到购物车", "to_cart"),
    ("添加到购物车的转化率， %", "to_cart_conversion_rate"),
    ("单笔费用，₽", "cost_per_order"),
    ("每次点击成本，₽", "cost_per_click"),
)

PAYMENT_TYPE_DISPLAY = {
    "CPC": "按点击付费",
    "CPO": "按订单付费",
    "CPM": "按千次展示付费",
}
PLACEMENT_DISPLAY = {
    "PLACEMENT_SEARCH_AND_CATEGORY": "搜索与推荐",
    "PLACEMENT_TOP_PROMOTION": "顶部推广",
    "PLACEMENT_SEARCH": "搜索",
    "PLACEMENT_CATEGORY": "推荐",
}


def _localized_code(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return value
    return ",".join(
        mapping.get(part.strip(), part.strip()) for part in value.split(",")
    )


class OzonAdvertEfficiencyService:
    async def _allowed_shop_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    def _query_kwargs(
        self, filters: OzonAdvertEfficiencyFilters, allowed_shop_ids: list[int]
    ) -> dict:
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "sku": filters.sku,
            "campaign_id": filters.campaign_id,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    def _item_dict(self, record: object, *, shop_names: dict[int, str]) -> dict:
        item = OzonAdvertEfficiencyItem.model_validate(record)
        row = item.model_dump(mode="python")
        row["shop_name"] = shop_names.get(item.shop_id)
        row["stat_date"] = item.stat_date.strftime("%Y-%m-%d")
        row["payment_type"] = _localized_code(item.payment_type, PAYMENT_TYPE_DISPLAY)
        row["placement"] = _localized_code(item.placement, PLACEMENT_DISPLAY)
        return row

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonAdvertEfficiencyFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonAdvertEfficiencyItem]:
        allowed = await self._allowed_shop_ids(db, user_id)
        rows, total = await crud_dwd_ozon_advert_efficiency_detail.list_items(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed),
        )
        items = []
        for row in rows:
            item = OzonAdvertEfficiencyItem.model_validate(row)
            item.payment_type = _localized_code(item.payment_type, PAYMENT_TYPE_DISPLAY)
            item.placement = _localized_code(item.placement, PLACEMENT_DISPLAY)
            items.append(item)
        return PageResponse[OzonAdvertEfficiencyItem](
            items=items, total=total, page=page, page_size=page_size
        )

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: OzonAdvertEfficiencyExportRequest,
    ) -> bytes:
        allowed = await self._allowed_shop_ids(db, user_id)
        if request.scope == "selected":
            records = await crud_dwd_ozon_advert_efficiency_detail.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            records = await crud_dwd_ozon_advert_efficiency_detail.list_for_export(
                db, **self._query_kwargs(request.filters, allowed)
            )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        return build_xlsx(
            OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS,
            [self._item_dict(record, shop_names=shop_names) for record in records],
            sheet_name="Ozon广告效率",
        )


ozon_advert_efficiency_service = OzonAdvertEfficiencyService()
