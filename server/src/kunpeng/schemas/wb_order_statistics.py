"""Wildberries statistics-order query and export schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kunpeng.utils.timezone import platform_tz

ExportScope = Literal["filtered", "selected"]


def to_moscow_local_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Attach Moscow timezone to WB Statistics API local timestamps."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=platform_tz())
    return value.astimezone(platform_tz())


class WBOrderStatisticsItem(BaseModel):
    """One statistics-order row mirroring the DWD table exactly."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    srid: str
    order_date: Optional[datetime] = None
    last_change_date: Optional[datetime] = None
    warehouse_name: Optional[str] = None
    warehouse_name_cn: Optional[str] = None
    country_name: Optional[str] = None
    country_name_cn: Optional[str] = None
    oblast_okrug_name: Optional[str] = None
    oblast_okrug_name_cn: Optional[str] = None
    region_name: Optional[str] = None
    region_name_cn: Optional[str] = None
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    barcode_ori: Optional[str] = None
    barcode_hand: Optional[str] = None
    category: Optional[str] = None
    category_cn: Optional[str] = None
    subject_name: Optional[str] = None
    subject_name_cn: Optional[str] = None
    tech_size: Optional[str] = None
    tech_size_cn: Optional[str] = None
    total_price: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    price_with_disc: Optional[Decimal] = None
    finished_price: Optional[Decimal] = None
    is_cancel: Optional[bool] = None
    cancel_date: Optional[datetime] = None
    sticker_id: Optional[str] = None
    g_number: Optional[str] = None

    @field_validator("order_date", "last_change_date", "cancel_date")
    @classmethod
    def normalize_statistics_datetime(
        cls, value: Optional[datetime]
    ) -> Optional[datetime]:
        return to_moscow_local_datetime(value)


class WBOrderStatisticsFilters(BaseModel):
    """Filters shared by statistics-order list and export operations."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    srid: Optional[str] = None
    warehouse_name: Optional[str] = None
    country_name: Optional[str] = None
    oblast_okrug_name: Optional[str] = None
    region_name: Optional[str] = None
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    category: Optional[str] = None
    subject_name: Optional[str] = None
    is_cancel: Optional[bool] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBOrderStatisticsFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBOrderStatisticsKey(BaseModel):
    """Composite key used by selected-row export."""

    shop_id: int
    srid: str = Field(min_length=1, max_length=255)


class WBOrderStatisticsExportRequest(BaseModel):
    """Request body for filtered or selected statistics-order export."""

    scope: ExportScope
    filters: WBOrderStatisticsFilters = Field(default_factory=WBOrderStatisticsFilters)
    selected_keys: list[WBOrderStatisticsKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected_export(self) -> "WBOrderStatisticsExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条统计订单")
        return self
