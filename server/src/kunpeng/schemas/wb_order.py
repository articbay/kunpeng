"""Wildberries order query and export schemas."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

from kunpeng.utils.timezone import platform_tz

ExportScope = Literal["filtered", "selected"]


def to_platform_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Interpret stored naive WB timestamps as UTC and return Moscow time."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(platform_tz())


class WBOrderItem(BaseModel):
    """One DWD order row plus normalized fields used for display and export."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    order_id: int
    supply_id: Optional[str] = None
    sticker_id: Optional[str] = None
    order_dt: Optional[datetime] = None
    title: Optional[str] = None
    title_cn: Optional[str] = None
    tech_size: Optional[str] = None
    tech_size_cn: Optional[str] = None
    color: Optional[str] = None
    color_cn: Optional[str] = None
    barcode_ori: Optional[str] = None
    barcode_hand: Optional[str] = None
    retail_price: Optional[Decimal] = None
    currency: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    warehouse_name_cn: Optional[str] = None
    wb_status: Optional[str] = None
    wb_status_cn: Optional[str] = None
    address: Optional[str] = None
    address_cn: Optional[str] = None
    is_b2b: Optional[bool] = None
    delivery_type: Optional[str] = None
    supplier_status: Optional[str] = None
    supplier_status_cn: Optional[str] = None
    is_cancellable: Optional[bool] = None
    price: Optional[Decimal] = None
    converted_price: Optional[Decimal] = None
    currency_code: Optional[int] = None
    converted_currency_code: Optional[int] = None
    order_price: Optional[Decimal] = None
    currency_name: Optional[str] = None
    office_id: Optional[int] = None
    cargo_type: Optional[int] = None
    cross_border_type: Optional[int] = None
    is_zero_order: Optional[bool] = None

    @field_validator("order_dt")
    @classmethod
    def normalize_order_datetime(cls, value: Optional[datetime]) -> Optional[datetime]:
        return to_platform_datetime(value)


class WBOrderFilters(BaseModel):
    """Filters shared by the list and filtered export operations."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    order_id: Optional[int] = None
    supply_id: Optional[str] = None
    sticker_id: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    warehouse_id: Optional[int] = None
    wb_status: Optional[str] = None
    supplier_status: Optional[str] = None
    delivery_type: Optional[str] = None
    is_cancellable: Optional[bool] = None
    is_b2b: Optional[bool] = None
    is_zero_order: Optional[bool] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBOrderFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBOrderKey(BaseModel):
    """Composite primary key used by selected-row export."""

    shop_id: int
    order_id: int


class WBOrderExportRequest(BaseModel):
    """Request body for filtered or selected order export."""

    scope: ExportScope
    filters: WBOrderFilters = Field(default_factory=WBOrderFilters)
    selected_keys: list[WBOrderKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "WBOrderExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条订单")
        return self
