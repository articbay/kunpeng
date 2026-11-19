"""Wildberries customer feedback query and export schemas."""

from datetime import date, datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kunpeng.utils.timezone import platform_tz

AnswerStatus = Literal["answered", "unanswered"]
ExportScope = Literal["filtered", "selected"]


def to_platform_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Interpret stored naive WB timestamps as UTC and return Moscow time."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(platform_tz())


class WBVOCFeedbackItem(BaseModel):
    """One DWD feedback row. Fields intentionally mirror the DWD table."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    feedback_id: str
    created_date: Optional[datetime] = None
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    product_valuation: Optional[int] = None
    brand_name: Optional[str] = None
    text: Optional[str] = None
    text_cn: Optional[str] = None
    pros: Optional[str] = None
    pros_cn: Optional[str] = None
    cons: Optional[str] = None
    cons_cn: Optional[str] = None
    user_name: Optional[str] = None
    color: Optional[str] = None
    color_cn: Optional[str] = None
    size: Optional[str] = None
    size_cn: Optional[str] = None
    answer: Optional[str] = None
    answer_cn: Optional[str] = None
    parent_feedback_id: Optional[str] = None
    child_feedback_id: Optional[str] = None

    @field_validator("created_date")
    @classmethod
    def normalize_created_date(cls, value: Optional[datetime]) -> Optional[datetime]:
        return to_platform_datetime(value)


class WBVOCFeedbackFilters(BaseModel):
    """Filters shared by the list and filtered export operations."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    product_valuations: list[int] = Field(default_factory=list)
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    brand_name: Optional[str] = None
    keyword: Optional[str] = None
    answer_status: Optional[AnswerStatus] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @field_validator("product_valuations")
    @classmethod
    def validate_product_valuations(cls, values: list[int]) -> list[int]:
        normalized = sorted(set(values))
        if any(value < 1 or value > 5 for value in normalized):
            raise ValueError("星级必须在 1 到 5 之间")
        return normalized

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBVOCFeedbackFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBVOCFeedbackKey(BaseModel):
    """Composite primary key used by selected-row export."""

    shop_id: int
    feedback_id: str = Field(min_length=1, max_length=255)


class WBVOCFeedbackExportRequest(BaseModel):
    """Request body for filtered or selected feedback export."""

    scope: ExportScope
    filters: WBVOCFeedbackFilters = Field(default_factory=WBVOCFeedbackFilters)
    selected_keys: list[WBVOCFeedbackKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "WBVOCFeedbackExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条评价")
        return self
