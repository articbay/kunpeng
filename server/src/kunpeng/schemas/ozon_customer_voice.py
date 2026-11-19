"""Ozon customer voice query and export schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kunpeng.schemas.ozon_return import to_platform_datetime

ExportScope = Literal["filtered", "selected"]


class OzonCustomerVoiceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    review_id: str
    month: Optional[str] = None
    offer_id: Optional[str] = None
    sku: Optional[int] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    posting_number: Optional[str] = None
    order_status: Optional[str] = None
    order_status_cn: Optional[str] = None
    review_text: Optional[str] = None
    review_text_cn: Optional[str] = None
    published_at: Optional[datetime] = None
    review_status: Optional[str] = None
    review_status_cn: Optional[str] = None
    rating: Optional[int] = None
    photos_amount: Optional[int] = None
    videos_amount: Optional[int] = None
    comments_amount: Optional[int] = None

    @model_validator(mode="after")
    def normalize_published_at(self) -> "OzonCustomerVoiceItem":
        self.published_at = to_platform_datetime(self.published_at)
        return self


class OzonCustomerVoiceFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    offer_id: Optional[str] = None
    sku: Optional[int] = None
    rating: Optional[int] = None
    order_status: Optional[str] = None
    review_status: Optional[str] = None
    keyword: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonCustomerVoiceFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonCustomerVoiceKey(BaseModel):
    shop_id: int
    review_id: str


class OzonCustomerVoiceExportRequest(BaseModel):
    scope: ExportScope
    filters: OzonCustomerVoiceFilters = Field(default_factory=OzonCustomerVoiceFilters)
    selected_keys: list[OzonCustomerVoiceKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected_export(self) -> "OzonCustomerVoiceExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条评价")
        return self
