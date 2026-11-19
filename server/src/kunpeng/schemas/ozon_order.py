"""Ozon unified order query and export schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExportScope = Literal["filtered", "selected"]


class OzonOrderItem(BaseModel):
    """One business row from the unified FBS/FBO order DWD table."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    fulfillment_type: Literal["FBS", "FBO"]
    posting_number: str
    sku: int
    order_type_name: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    in_process_month: Optional[date] = None
    in_process_date: Optional[date] = None
    in_process_hour: Optional[int] = None
    in_process_at: Optional[datetime] = None
    shipment_date: Optional[datetime] = None
    status_code: Optional[str] = None
    substatus_code: Optional[str] = None
    status_name_cn: Optional[str] = None
    delivery_date: Optional[datetime] = None
    transferred_to_delivery_at: Optional[datetime] = None
    delivery_duration_1_hours: Optional[Decimal] = None
    delivery_duration_2_hours: Optional[Decimal] = None
    delivery_level_1: Optional[str] = None
    delivery_level_2: Optional[str] = None
    shipment_amount: Optional[Decimal] = None
    shipment_currency: Optional[str] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    offer_id: Optional[str] = None
    seller_price: Optional[Decimal] = None
    product_currency: Optional[str] = None
    buyer_paid_amount: Optional[Decimal] = None
    buyer_currency: Optional[str] = None
    quantity: Optional[int] = None
    delivery_fee: Optional[Decimal] = None
    related_posting_number: Optional[str] = None
    is_marketplace_buyout: Optional[bool] = None
    old_price: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    promotion_actions: Optional[Any] = None
    product_volume_weight: Optional[Decimal] = None
    cluster_from: Optional[str] = None
    cluster_to: Optional[str] = None
    promised_delivery_at: Optional[datetime] = None
    shipment_assessment: Optional[str] = None
    ozon_warehouse_name: Optional[str] = None
    delivery_region: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_city_cn: Optional[str] = None
    delivery_type: Optional[str] = None
    is_premium: Optional[bool] = None
    is_legal: Optional[bool] = None
    payment_type: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    addressee_name: Optional[str] = None
    buyer_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    postal_code: Optional[str] = None
    seller_warehouse_name: Optional[str] = None
    shipment_method: Optional[str] = None
    logistics_company: Optional[str] = None
    delivery_method_name: Optional[str] = None
    shipment_date_without_delay: Optional[datetime] = None
    cancellation_at: Optional[datetime] = None
    declared_total_weight: Optional[Decimal] = None
    actual_total_weight: Optional[Decimal] = None
    shipment_volume_weight: Optional[Decimal] = None
    product_color: Optional[str] = None
    product_size: Optional[str] = None


class OzonOrderFilters(BaseModel):
    """Filters shared by list and filtered export."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    fulfillment_type: Optional[Literal["FBS", "FBO"]] = None
    posting_number: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    sku: Optional[int] = None
    offer_id: Optional[str] = None
    status_code: Optional[str] = None
    substatus_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    delivery_region: Optional[str] = None
    delivery_city: Optional[str] = None
    payment_type: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonOrderFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonOrderKey(BaseModel):
    """Composite primary key used by selected-row export."""

    shop_id: int
    fulfillment_type: Literal["FBS", "FBO"]
    posting_number: str
    sku: int


class OzonOrderExportRequest(BaseModel):
    """Request body for filtered or selected order export."""

    scope: ExportScope
    filters: OzonOrderFilters = Field(default_factory=OzonOrderFilters)
    selected_keys: list[OzonOrderKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "OzonOrderExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条订单")
        return self
