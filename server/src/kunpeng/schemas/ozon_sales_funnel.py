"""Ozon sales-funnel query and export schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExportScope = Literal["filtered", "selected"]


class OzonSalesFunnelItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_ods_id: int
    shop_id: int
    offer_id: Optional[str] = None
    sku: int
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    category_name: Optional[str] = None
    category_name_cn: Optional[str] = None
    stat_date: date
    hits_view_search: Optional[int] = None
    hits_view_pdp: Optional[int] = None
    hits_view: Optional[int] = None
    session_view_search: Optional[int] = None
    session_view_pdp: Optional[int] = None
    session_view: Optional[int] = None
    hits_tocart_search: Optional[int] = None
    hits_tocart_pdp: Optional[int] = None
    hits_tocart: Optional[int] = None
    conv_tocart_search: Optional[Decimal] = None
    conv_tocart_pdp: Optional[Decimal] = None
    conv_tocart: Optional[Decimal] = None
    ordered_units: Optional[int] = None
    revenue: Optional[Decimal] = None
    delivered_units: Optional[int] = None
    cancellations: Optional[int] = None
    returns: Optional[int] = None
    position_category: Optional[Decimal] = None
    cart_to_order_rate: Optional[Decimal] = None
    has_core_metrics: bool
    has_outcome_metrics: bool
    source_synced_at: Optional[datetime] = None
    create_time: datetime
    update_time: Optional[datetime] = None


class OzonSalesFunnelFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    sku: Optional[int] = None
    offer_id: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonSalesFunnelFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonSalesFunnelKey(BaseModel):
    shop_id: int
    stat_date: date
    sku: int


class OzonSalesFunnelExportRequest(BaseModel):
    scope: ExportScope
    filters: OzonSalesFunnelFilters = Field(default_factory=OzonSalesFunnelFilters)
    selected_keys: list[OzonSalesFunnelKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected_export(self) -> "OzonSalesFunnelExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条销售漏斗明细")
        return self
