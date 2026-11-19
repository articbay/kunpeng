"""Wildberries return query and export schemas."""

from datetime import date, datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kunpeng.utils.timezone import platform_tz

ExportScope = Literal["filtered", "selected"]


def to_platform_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Interpret stored naive WB timestamps as UTC and return Moscow time."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(platform_tz())


class WBReturnItem(BaseModel):
    """One DWD return row. Fields intentionally mirror the DWD table."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    brand: Optional[str] = None
    subject_name: Optional[str] = None
    subject_name_cn: Optional[str] = None
    barcode_ori: Optional[str] = None
    barcode_hand: Optional[str] = None
    nm_id: Optional[int] = None
    sticker_id: Optional[str] = None
    status: Optional[str] = None
    status_cn: Optional[str] = None
    ready_to_return_dt: Optional[datetime] = None
    completed_dt: Optional[datetime] = None
    expired_dt: Optional[datetime] = None
    return_type: Optional[str] = None
    return_type_cn: Optional[str] = None
    order_dt: Optional[date] = None
    reason: Optional[str] = None
    reason_cn: Optional[str] = None
    order_id: Optional[int] = None
    srid: str
    dst_office_address: Optional[str] = None
    dst_office_address_cn: Optional[str] = None
    dst_office_id: Optional[int] = None

    @field_validator("ready_to_return_dt", "completed_dt", "expired_dt")
    @classmethod
    def normalize_lifecycle_datetime(
        cls, value: Optional[datetime]
    ) -> Optional[datetime]:
        return to_platform_datetime(value)


class WBReturnFilters(BaseModel):
    """Filters shared by the list and filtered export operations."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    nm_id: Optional[int] = None
    order_id: Optional[int] = None
    brand: Optional[str] = None
    subject_name: Optional[str] = None
    status: Optional[str] = None
    return_type: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBReturnFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBReturnKey(BaseModel):
    """Composite primary key used by selected-row export."""

    shop_id: int
    srid: str = Field(min_length=1, max_length=255)


class WBReturnExportRequest(BaseModel):
    """Request body for filtered or selected return export."""

    scope: ExportScope
    filters: WBReturnFilters = Field(default_factory=WBReturnFilters)
    selected_keys: list[WBReturnKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "WBReturnExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条退货记录")
        return self
