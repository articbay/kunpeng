"""Wildberries customer question query and export schemas."""

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


class WBVOCQuestionItem(BaseModel):
    """One DWD question row. Fields intentionally mirror the DWD table."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    question_id: str
    created_date: Optional[datetime] = None
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    brand_name: Optional[str] = None
    text: Optional[str] = None
    text_cn: Optional[str] = None
    answer: Optional[str] = None
    answer_cn: Optional[str] = None

    @field_validator("created_date")
    @classmethod
    def normalize_created_date(cls, value: Optional[datetime]) -> Optional[datetime]:
        return to_platform_datetime(value)


class WBVOCQuestionFilters(BaseModel):
    """Filters shared by the list and filtered export operations."""

    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    supplier_article: Optional[str] = None
    nm_id: Optional[int] = None
    brand_name: Optional[str] = None
    keyword: Optional[str] = None
    answer_status: Optional[AnswerStatus] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBVOCQuestionFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBVOCQuestionKey(BaseModel):
    """Composite primary key used by selected-row export."""

    shop_id: int
    question_id: str = Field(min_length=1, max_length=255)


class WBVOCQuestionExportRequest(BaseModel):
    """Request body for filtered or selected question export."""

    scope: ExportScope
    filters: WBVOCQuestionFilters = Field(default_factory=WBVOCQuestionFilters)
    selected_keys: list[WBVOCQuestionKey] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_selected_export(self) -> "WBVOCQuestionExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条提问")
        return self
