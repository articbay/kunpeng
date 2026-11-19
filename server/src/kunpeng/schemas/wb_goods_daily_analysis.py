"""Schemas for the Wildberries goods daily analysis DWM."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WBGoodsDailyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stat_date: date
    shop_id: int
    nm_id: int
    vendor_code: Optional[str] = None
    product_title: Optional[str] = None
    product_title_cn: Optional[str] = None
    brand_name: Optional[str] = None
    subject_name: Optional[str] = None
    subject_name_cn: Optional[str] = None
    has_funnel_data: bool
    has_order_data: bool
    has_return_data: bool
    has_ad_data: bool
    product_rating: Optional[Decimal] = None
    feedback_rating: Optional[Decimal] = None
    traffic_clicks: Optional[int] = None
    traffic_cart_qty: Optional[int] = None
    traffic_wishlist_qty: Optional[int] = None
    funnel_order_qty: Optional[int] = None
    funnel_buyout_qty: Optional[int] = None
    funnel_cancel_qty: Optional[int] = None
    funnel_order_amount: Optional[Decimal] = None
    funnel_buyout_amount: Optional[Decimal] = None
    funnel_cancel_amount: Optional[Decimal] = None
    order_cnt: int
    order_qty: int
    cancelled_order_cnt: int
    cancelled_qty: int
    order_amount_sum: Optional[Decimal] = None
    finished_amount_sum: Optional[Decimal] = None
    return_cnt: int
    return_qty: int
    return_ready_cnt: int
    return_completed_cnt: int
    return_expired_cnt: int
    ad_campaign_cnt: Optional[int] = None
    ad_views: Optional[int] = None
    ad_clicks: Optional[int] = None
    ad_to_cart: Optional[int] = None
    ad_order_cnt: Optional[int] = None
    ad_cancelled_cnt: Optional[int] = None
    ad_sales_qty: Optional[int] = None
    ad_spend_amount: Optional[Decimal] = None
    ad_attributed_sales_amount: Optional[Decimal] = None
    ad_currency: Optional[str] = None
    has_ad_currency_conflict: bool
    traffic_cart_rate: Optional[Decimal] = None
    traffic_order_rate: Optional[Decimal] = None
    traffic_buyout_rate: Optional[Decimal] = None
    order_cancel_rate: Optional[Decimal] = None
    return_rate_ordered: Optional[Decimal] = None
    return_rate_buyout: Optional[Decimal] = None
    ad_ctr: Optional[Decimal] = None
    ad_cart_rate: Optional[Decimal] = None
    ad_cvr: Optional[Decimal] = None
    ad_cpc: Optional[Decimal] = None
    ad_cpo: Optional[Decimal] = None
    ad_roas: Optional[Decimal] = None
    ad_drr: Optional[Decimal] = None
    ad_click_share: Optional[Decimal] = None
    estimated_organic_clicks: Optional[int] = None
    has_click_scope_conflict: bool
    create_time: datetime
    update_time: Optional[datetime] = None


WBGoodsDataStatus = Literal["has_orders", "has_returns", "has_funnel", "has_ad"]
WBGoodsAnomaly = Literal[
    "ad_spend_no_orders",
    "high_return_rate",
    "clicks_no_cart",
    "cart_no_orders",
    "high_cancel_rate",
    "click_scope_conflict",
    "ad_currency_conflict",
]


class WBGoodsDailyFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    nm_id: Optional[int] = None
    vendor_code: Optional[str] = None
    keyword: Optional[str] = None
    data_status: Optional[WBGoodsDataStatus] = None
    anomaly: Optional[WBGoodsAnomaly] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBGoodsDailyFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBGoodsDailyKey(BaseModel):
    stat_date: date
    shop_id: int
    nm_id: int


class WBGoodsDailyExportRequest(BaseModel):
    scope: Literal["filtered", "selected"]
    filters: WBGoodsDailyFilters = Field(default_factory=WBGoodsDailyFilters)
    selected_keys: list[WBGoodsDailyKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected(self) -> "WBGoodsDailyExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条商品日记录")
        return self


class WBGoodsDailyMetrics(BaseModel):
    sales_amount: Decimal = Decimal("0")
    order_qty: int = 0
    funnel_order_qty: int = 0
    has_funnel_data: bool = False
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    ad_attributed_sales: Decimal = Decimal("0")
    ad_roas: Optional[Decimal] = None
    ad_drr: Optional[Decimal] = None
    sales_currency: Optional[str] = None
    ad_currency: Optional[str] = None
    has_currency_conflict: bool = False


class WBGoodsDailyTrendPoint(BaseModel):
    stat_date: date
    sales_amount: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")


class WBGoodsDailyRankingItem(BaseModel):
    nm_id: int
    vendor_code: Optional[str] = None
    product_title_cn: Optional[str] = None
    product_title: Optional[str] = None
    sales_amount: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    ad_roas: Optional[Decimal] = None


class WBGoodsDailySummary(BaseModel):
    metrics: WBGoodsDailyMetrics
    trend: list[WBGoodsDailyTrendPoint] = Field(default_factory=list)
    ranking: list[WBGoodsDailyRankingItem] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class WBGoodsPeriodMetrics(BaseModel):
    sales_amount: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    ad_attributed_sales: Decimal = Decimal("0")
    ad_roas: Optional[Decimal] = None


class WBGoodsProductShopDetail(BaseModel):
    shop_id: int
    shop_name: Optional[str] = None
    metrics: WBGoodsPeriodMetrics


class WBGoodsProductDetail(BaseModel):
    nm_id: int
    vendor_code: Optional[str] = None
    product_title: Optional[str] = None
    product_title_cn: Optional[str] = None
    brand_name: Optional[str] = None
    subject_name: Optional[str] = None
    subject_name_cn: Optional[str] = None
    period_from: date
    period_to: date
    metrics: WBGoodsPeriodMetrics
    shops: list[WBGoodsProductShopDetail] = Field(default_factory=list)
