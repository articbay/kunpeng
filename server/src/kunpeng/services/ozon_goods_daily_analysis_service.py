"""Ozon goods daily analysis listing, summary, detail and export."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwm.ozon.goods_daily_analysis import (
    crud_dwm_ozon_goods_daily_analysis,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_goods_daily_analysis import (
    OzonGoodsDailyExportRequest,
    OzonGoodsDailyFilters,
    OzonGoodsDailyItem,
    OzonGoodsDailySummary,
    OzonGoodsProductDetail,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("统计日期", "stat_date"),
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("Ozon SKU", "sku"),
    ("卖家货号", "offer_id"),
    ("商品名称（中文）", "product_name_cn"),
    ("商品名称", "product_name"),
    ("品类（中文）", "category_name_cn"),
    ("品类", "category_name"),
    ("去重发货单数", "order_cnt"),
    ("订单商品行数", "order_line_cnt"),
    ("下单件数", "order_qty"),
    ("已送达件数", "delivered_qty"),
    ("已取消件数", "cancelled_qty"),
    ("销售金额", "sales_amount_sum"),
    ("销售币种", "sales_currency"),
    ("退货单数", "return_cnt"),
    ("退货件数", "return_qty"),
    ("按下单件数退货率", "return_rate_ordered"),
    ("按送达件数退货率", "return_rate_delivered"),
    ("退货商品金额", "return_amount_sum"),
    ("退货金额币种", "return_amount_currency"),
    ("仓储费", "storage_fee_sum"),
    ("仓储费币种", "storage_fee_currency"),
    ("销毁费", "utilization_fee_sum"),
    ("销毁费币种", "utilization_fee_currency"),
    ("退货佣金", "commission_amount_sum"),
    ("佣金币种", "commission_currency"),
    ("金额存在冲突", "has_currency_conflict"),
    ("存在漏斗数据", "has_funnel_data"),
    ("流量指标已返回", "has_traffic_metrics"),
    ("漏斗下单件数", "funnel_ordered_units"),
    ("漏斗下单金额", "funnel_revenue"),
    ("总展示/浏览次数", "traffic_views"),
    ("总访问用户数", "traffic_visitors"),
    ("总加购次数", "traffic_to_cart"),
    ("流量加购率", "traffic_cart_rate"),
    ("存在广告数据", "has_ad_data"),
    ("广告活动数", "ad_campaign_cnt"),
    ("广告展现量", "ad_views"),
    ("广告点击数", "ad_clicks"),
    ("广告加购数", "ad_to_cart"),
    ("广告花费", "ad_spend_amount"),
    ("广告花费币种", "ad_spend_currency"),
    ("广告归因订单数", "ad_attributed_order_cnt"),
    ("广告归因销售额", "ad_attributed_sales_amount"),
    ("广告CTR", "ad_ctr"),
    ("广告加购率", "ad_cart_rate"),
    ("广告CPC", "ad_cpc"),
    ("广告CPO", "ad_cpo"),
    ("广告ROAS", "ad_roas"),
    ("广告DRR", "ad_drr"),
    ("创建时间", "create_time"),
    ("更新时间", "update_time"),
)


class OzonGoodsDailyAnalysisService:
    async def _allowed(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    @staticmethod
    def _kwargs(filters: OzonGoodsDailyFilters, allowed: list[int]) -> dict:
        return {"allowed_shop_ids": allowed, **filters.model_dump(mode="python")}

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonGoodsDailyFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonGoodsDailyItem]:
        allowed = await self._allowed(db, user_id)
        rows, total = await crud_dwm_ozon_goods_daily_analysis.list_items(
            db, page=page, page_size=page_size, **self._kwargs(filters, allowed)
        )
        return PageResponse[OzonGoodsDailyItem](
            items=[OzonGoodsDailyItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def summary(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonGoodsDailyFilters,
        ranking_metric: str,
    ) -> OzonGoodsDailySummary:
        allowed = await self._allowed(db, user_id)
        result = await crud_dwm_ozon_goods_daily_analysis.get_summary(
            db,
            ranking_metric=ranking_metric,
            **self._kwargs(filters, allowed),
        )
        return OzonGoodsDailySummary.model_validate(result)

    async def product_detail(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        sku: int,
        filters: OzonGoodsDailyFilters,
    ) -> OzonGoodsProductDetail:
        allowed = await self._allowed(db, user_id)
        query = self._kwargs(filters, allowed)
        query["sku"] = sku
        result = await crud_dwm_ozon_goods_daily_analysis.get_product_detail(
            db, **query
        )
        if result is None:
            raise HTTPException(status_code=404, detail="商品周期数据不存在")
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for shop in result["shops"]:
            shop["shop_name"] = shop_names.get(shop["shop_id"])
        return OzonGoodsProductDetail.model_validate(result)

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: OzonGoodsDailyExportRequest,
    ) -> bytes:
        allowed = await self._allowed(db, user_id)
        if request.scope == "selected":
            rows = await crud_dwm_ozon_goods_daily_analysis.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            rows = await crud_dwm_ozon_goods_daily_analysis.list_for_export(
                db, **self._kwargs(request.filters, allowed)
            )
        data = [
            OzonGoodsDailyItem.model_validate(row).model_dump(mode="python")
            for row in rows
        ]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for row in data:
            row["shop_name"] = shop_names.get(row["shop_id"])
        return build_xlsx(EXPORT_COLUMNS, data, sheet_name="Ozon商品日分析")


ozon_goods_daily_analysis_service = OzonGoodsDailyAnalysisService()
