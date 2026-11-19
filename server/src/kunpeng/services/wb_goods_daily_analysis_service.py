"""Wildberries goods daily analysis listing, summary, detail and export."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwm.wildberries.goods_daily_analysis import (
    crud_dwm_wb_goods_daily_analysis,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_goods_daily_analysis import (
    WBGoodsDailyExportRequest,
    WBGoodsDailyFilters,
    WBGoodsDailyItem,
    WBGoodsDailySummary,
    WBGoodsProductDetail,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("统计日期", "stat_date"),
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("WB商品ID", "nm_id"),
    ("卖家货号", "vendor_code"),
    ("商品名称（中文）", "product_title_cn"),
    ("商品名称", "product_title"),
    ("品牌", "brand_name"),
    ("品类（中文）", "subject_name_cn"),
    ("品类", "subject_name"),
    ("存在漏斗数据", "has_funnel_data"),
    ("存在订单数据", "has_order_data"),
    ("存在退货数据", "has_return_data"),
    ("存在广告数据", "has_ad_data"),
    ("商品评分", "product_rating"),
    ("评论评分", "feedback_rating"),
    ("商品点击数", "traffic_clicks"),
    ("商品加购数", "traffic_cart_qty"),
    ("商品收藏数", "traffic_wishlist_qty"),
    ("漏斗下单件数", "funnel_order_qty"),
    ("漏斗售出件数", "funnel_buyout_qty"),
    ("漏斗取消件数", "funnel_cancel_qty"),
    ("漏斗订单金额", "funnel_order_amount"),
    ("漏斗售出金额", "funnel_buyout_amount"),
    ("漏斗取消金额", "funnel_cancel_amount"),
    ("去重订单数", "order_cnt"),
    ("下单件数", "order_qty"),
    ("取消订单数", "cancelled_order_cnt"),
    ("取消件数", "cancelled_qty"),
    ("折后订单金额", "order_amount_sum"),
    ("最终价格合计", "finished_amount_sum"),
    ("退货记录数", "return_cnt"),
    ("退货件数", "return_qty"),
    ("已准备退货数", "return_ready_cnt"),
    ("已领取退货数", "return_completed_cnt"),
    ("已过期退货数", "return_expired_cnt"),
    ("广告活动数", "ad_campaign_cnt"),
    ("广告曝光量", "ad_views"),
    ("广告点击数", "ad_clicks"),
    ("广告加购数", "ad_to_cart"),
    ("广告归因订单数", "ad_order_cnt"),
    ("广告取消数", "ad_cancelled_cnt"),
    ("广告归因销量", "ad_sales_qty"),
    ("广告花费", "ad_spend_amount"),
    ("广告归因销售额", "ad_attributed_sales_amount"),
    ("广告币种", "ad_currency"),
    ("广告币种冲突", "has_ad_currency_conflict"),
    ("流量加购率", "traffic_cart_rate"),
    ("流量下单率", "traffic_order_rate"),
    ("流量售出率", "traffic_buyout_rate"),
    ("订单取消率", "order_cancel_rate"),
    ("按下单件数退货率", "return_rate_ordered"),
    ("按售出件数退货率", "return_rate_buyout"),
    ("广告CTR", "ad_ctr"),
    ("广告加购率", "ad_cart_rate"),
    ("广告CVR", "ad_cvr"),
    ("广告CPC", "ad_cpc"),
    ("广告CPO", "ad_cpo"),
    ("广告ROAS", "ad_roas"),
    ("广告DRR", "ad_drr"),
    ("广告点击占比", "ad_click_share"),
    ("估算自然点击", "estimated_organic_clicks"),
    ("点击口径冲突", "has_click_scope_conflict"),
    ("创建时间", "create_time"),
    ("更新时间", "update_time"),
)


class WBGoodsDailyAnalysisService:
    async def _allowed(self, db: AsyncSession, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    @staticmethod
    def _kwargs(filters: WBGoodsDailyFilters, allowed: list[int]) -> dict:
        return {"allowed_shop_ids": allowed, **filters.model_dump(mode="python")}

    async def list_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBGoodsDailyFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBGoodsDailyItem]:
        allowed = await self._allowed(db, user_id)
        rows, total = await crud_dwm_wb_goods_daily_analysis.list_items(
            db, page=page, page_size=page_size, **self._kwargs(filters, allowed)
        )
        return PageResponse[WBGoodsDailyItem](
            items=[WBGoodsDailyItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def summary(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBGoodsDailyFilters,
        ranking_metric: str,
    ) -> WBGoodsDailySummary:
        allowed = await self._allowed(db, user_id)
        result = await crud_dwm_wb_goods_daily_analysis.get_summary(
            db,
            ranking_metric=ranking_metric,
            **self._kwargs(filters, allowed),
        )
        return WBGoodsDailySummary.model_validate(result)

    async def product_detail(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        nm_id: int,
        filters: WBGoodsDailyFilters,
    ) -> WBGoodsProductDetail:
        allowed = await self._allowed(db, user_id)
        query = self._kwargs(filters, allowed)
        query["nm_id"] = nm_id
        result = await crud_dwm_wb_goods_daily_analysis.get_product_detail(db, **query)
        if result is None:
            raise HTTPException(status_code=404, detail="商品周期数据不存在")
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for shop in result["shops"]:
            shop["shop_name"] = shop_names.get(shop["shop_id"])
        return WBGoodsProductDetail.model_validate(result)

    async def export_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request: WBGoodsDailyExportRequest,
    ) -> bytes:
        allowed = await self._allowed(db, user_id)
        if request.scope == "selected":
            rows = await crud_dwm_wb_goods_daily_analysis.list_by_keys(
                db, allowed_shop_ids=allowed, keys=request.selected_keys
            )
        else:
            rows = await crud_dwm_wb_goods_daily_analysis.list_for_export(
                db, **self._kwargs(request.filters, allowed)
            )
        data = [
            WBGoodsDailyItem.model_validate(row).model_dump(mode="python")
            for row in rows
        ]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed)
        for row in data:
            row["shop_name"] = shop_names.get(row["shop_id"])
        return build_xlsx(EXPORT_COLUMNS, data, sheet_name="WB商品日分析")


wb_goods_daily_analysis_service = WBGoodsDailyAnalysisService()
