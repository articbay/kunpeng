"""Schemas for the Ozon goods daily analysis DWM."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OzonGoodsDailyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stat_date: date
    shop_id: int
    sku: int
    offer_id: Optional[str] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    category_name: Optional[str] = None
    category_name_cn: Optional[str] = None
    order_cnt: int
    order_line_cnt: int
    order_qty: int
    delivered_qty: int
    cancelled_qty: int
    sales_amount_sum: Optional[Decimal] = None
    sales_currency: Optional[str] = None
    return_cnt: int
    return_qty: int
    return_amount_sum: Optional[Decimal] = None
    return_amount_currency: Optional[str] = None
    storage_fee_sum: Optional[Decimal] = None
    storage_fee_currency: Optional[str] = None
    utilization_fee_sum: Optional[Decimal] = None
    utilization_fee_currency: Optional[str] = None
    commission_amount_sum: Optional[Decimal] = None
    commission_currency: Optional[str] = None
    return_rate_ordered: Decimal
    return_rate_delivered: Decimal
    has_currency_conflict: bool
    has_funnel_data: bool
    has_traffic_metrics: bool
    funnel_ordered_units: Optional[int] = None
    funnel_revenue: Optional[Decimal] = None
    traffic_views_search: Optional[int] = None
    traffic_views_pdp: Optional[int] = None
    traffic_views: Optional[int] = None
    traffic_visitors_search: Optional[int] = None
    traffic_visitors_pdp: Optional[int] = None
    traffic_visitors: Optional[int] = None
    traffic_to_cart_search: Optional[int] = None
    traffic_to_cart_pdp: Optional[int] = None
    traffic_to_cart: Optional[int] = None
    traffic_cart_rate: Optional[Decimal] = None
    has_ad_data: bool
    ad_campaign_cnt: Optional[int] = None
    ad_views: Optional[int] = None
    ad_clicks: Optional[int] = None
    ad_to_cart: Optional[int] = None
    ad_spend_amount: Optional[Decimal] = None
    ad_spend_currency: Optional[str] = None
    ad_attributed_order_cnt: Optional[int] = None
    ad_attributed_sales_amount: Optional[Decimal] = None
    ad_ctr: Optional[Decimal] = None
    ad_cart_rate: Optional[Decimal] = None
    ad_cpc: Optional[Decimal] = None
    ad_cpo: Optional[Decimal] = None
    ad_roas: Optional[Decimal] = None
    ad_drr: Optional[Decimal] = None
    create_time: datetime
    update_time: Optional[datetime] = None


GoodsDataStatus = Literal[
    "has_orders", "has_returns", "has_funnel", "has_ad", "has_traffic"
]
GoodsAnomaly = Literal[
    "ad_spend_no_orders", "high_return_rate", "clicks_no_cart", "cart_no_orders"
]


class OzonGoodsDailyFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    sku: Optional[int] = None
    offer_id: Optional[str] = None
    keyword: Optional[str] = None
    data_status: Optional[GoodsDataStatus] = None
    anomaly: Optional[GoodsAnomaly] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonGoodsDailyFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonGoodsDailyKey(BaseModel):
    stat_date: date
    shop_id: int
    sku: int


class OzonGoodsDailyExportRequest(BaseModel):
    scope: Literal["filtered", "selected"]
    filters: OzonGoodsDailyFilters = Field(default_factory=OzonGoodsDailyFilters)
    selected_keys: list[OzonGoodsDailyKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected(self) -> "OzonGoodsDailyExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条商品日记录")
        return self


class OzonGoodsDailyMetrics(BaseModel):
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


class OzonGoodsDailyTrendPoint(BaseModel):
    stat_date: date
    sales_amount: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")


class OzonGoodsDailyRankingItem(BaseModel):
    sku: int
    offer_id: Optional[str] = None
    product_name_cn: Optional[str] = None
    product_name: Optional[str] = None
    sales_amount: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    ad_roas: Optional[Decimal] = None


class OzonGoodsDailySummary(BaseModel):
    metrics: OzonGoodsDailyMetrics
    trend: list[OzonGoodsDailyTrendPoint] = Field(default_factory=list)
    ranking: list[OzonGoodsDailyRankingItem] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class OzonGoodsPeriodMetrics(BaseModel):
    sales_amount: Decimal = Decimal("0")
    order_qty: int = 0
    return_qty: int = 0
    return_rate: Decimal = Decimal("0")
    ad_spend: Decimal = Decimal("0")
    ad_attributed_sales: Decimal = Decimal("0")
    ad_roas: Optional[Decimal] = None


class OzonGoodsProductShopDetail(BaseModel):
    shop_id: int
    shop_name: Optional[str] = None
    metrics: OzonGoodsPeriodMetrics


class OzonGoodsProductDetail(BaseModel):
    sku: int
    offer_id: Optional[str] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    category_name: Optional[str] = None
    category_name_cn: Optional[str] = None
    period_from: date
    period_to: date
    metrics: OzonGoodsPeriodMetrics
    shops: list[OzonGoodsProductShopDetail] = Field(default_factory=list)
