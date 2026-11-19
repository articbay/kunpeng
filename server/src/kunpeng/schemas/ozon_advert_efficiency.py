"""Ozon advertising efficiency query and export schemas."""

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExportScope = Literal["filtered", "selected"]


class OzonAdvertEfficiencyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    stat_date: date
    sku: int
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    category_name: Optional[str] = None
    category_name_cn: Optional[str] = None
    payment_type: Optional[str] = None
    placement: Optional[str] = None
    campaign_id: str
    campaign_name: Optional[str] = None
    money_spent: Optional[Decimal] = None
    drr: Optional[Decimal] = None
    orders_money: Optional[Decimal] = None
    orders: Optional[int] = None
    ctr: Optional[Decimal] = None
    views: Optional[int] = None
    clicks: Optional[int] = None
    to_cart: Optional[int] = None
    to_cart_conversion_rate: Optional[Decimal] = None
    cost_per_order: Optional[Decimal] = None
    cost_per_click: Optional[Decimal] = None


class OzonAdvertEfficiencyFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    sku: Optional[int] = None
    campaign_id: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonAdvertEfficiencyFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonAdvertEfficiencyKey(BaseModel):
    shop_id: int
    stat_date: date
    sku: int
    campaign_id: str


class OzonAdvertEfficiencyExportRequest(BaseModel):
    scope: ExportScope
    filters: OzonAdvertEfficiencyFilters = Field(
        default_factory=OzonAdvertEfficiencyFilters
    )
    selected_keys: list[OzonAdvertEfficiencyKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected_export(self) -> "OzonAdvertEfficiencyExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条广告明细")
        return self
