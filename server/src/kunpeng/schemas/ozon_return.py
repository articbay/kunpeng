"""Ozon return query and export schemas."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

from kunpeng.utils.timezone import platform_tz

ExportScope = Literal["filtered", "selected"]


def to_platform_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Interpret stored naive Ozon timestamps as UTC and return Moscow time."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(platform_tz())


class OzonReturnItem(BaseModel):
    """One DWD Ozon return row; fields mirror the DWD table."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    return_id: int
    nm_id: int
    schema: Optional[str] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    posting_number: Optional[str] = None
    offer_id: Optional[str] = None
    order_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    status_id: Optional[int] = None
    status_display_name: Optional[str] = None
    status_display_name_cn: Optional[str] = None
    status_sys_name: Optional[str] = None
    status_change_at: Optional[datetime] = None
    compensation_status_id: Optional[int] = None
    compensation_status_display_name: Optional[str] = None
    compensation_status_display_name_cn: Optional[str] = None
    compensation_status_sys_name: Optional[str] = None
    compensation_status_change_at: Optional[datetime] = None
    return_reason_name: Optional[str] = None
    return_reason_name_cn: Optional[str] = None
    buyer_comment: Optional[str] = None
    buyer_comment_cn: Optional[str] = None
    quantity: Optional[int] = None
    is_opened: Optional[bool] = None
    target_place_name: Optional[str] = None
    target_place_name_cn: Optional[str] = None
    target_place_address: Optional[str] = None
    target_place_address_cn: Optional[str] = None
    ready_to_pickup_at: Optional[datetime] = None
    place_name: Optional[str] = None
    place_name_cn: Optional[str] = None
    picked_up_at: Optional[datetime] = None
    storage_days: Optional[int] = None
    storage_expire_at: Optional[datetime] = None
    logistic_barcode: Optional[str] = None
    storage_fee_amount: Optional[Decimal] = None
    storage_fee_currency: Optional[str] = None
    utilization_fee_amount: Optional[Decimal] = None
    utilization_fee_currency: Optional[str] = None
    price_amount: Optional[Decimal] = None
    price_currency: Optional[str] = None
    commission_percent: Optional[Decimal] = None
    commission_amount: Optional[Decimal] = None
    commission_currency: Optional[str] = None
    price_without_commission_amount: Optional[Decimal] = None
    price_without_commission_currency: Optional[str] = None

    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    category_name_cn: Optional[str] = None
    product_barcode: Optional[str] = None
    exemplar_id: Optional[int] = None
    utilization_forecast_at: Optional[datetime] = None
    pickup_duration_hours: Optional[Decimal] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    srid: Optional[str] = None
    place_id: Optional[int] = None
    place_address: Optional[str] = None
    place_address_cn: Optional[str] = None
    target_place_id: Optional[int] = None
    return_type: Optional[str] = None
    is_super_econom: Optional[bool] = None

    @field_validator(
        "status_change_at",
        "compensation_status_change_at",
        "ready_to_pickup_at",
        "picked_up_at",
        "storage_expire_at",
        "utilization_forecast_at",
        "order_date",
        "return_date",
    )
    @classmethod
    def normalize_datetime(cls, value: Optional[datetime]) -> Optional[datetime]:
        return to_platform_datetime(value)


class OzonReturnFilters(BaseModel):
    """Filters shared by listing and filtered export."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    return_id: Optional[int] = None
    nm_id: Optional[int] = None
    posting_number: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    offer_id: Optional[str] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    return_type: Optional[str] = None
    schema: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonReturnFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonReturnKey(BaseModel):
    """Composite primary key for selected-row export."""

    shop_id: int
    return_id: int
    nm_id: int


class OzonReturnExportRequest(BaseModel):
    """Request body for filtered or selected Ozon return export."""

    scope: ExportScope
    filters: OzonReturnFilters = Field(default_factory=OzonReturnFilters)
    selected_keys: list[OzonReturnKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "OzonReturnExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条退货记录")
        return self
