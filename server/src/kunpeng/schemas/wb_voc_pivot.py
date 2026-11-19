"""Wildberries customer-voice Pivot export schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class WBVOCPivotFilters(BaseModel):
    """Filters shared by the three read-only DWD queries."""

    shop_id: Optional[int] = Field(default=None, gt=0)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    nm_id: Optional[int] = Field(default=None, gt=0)
    supplier_article: Optional[str] = Field(default=None, max_length=255)
    brand_name: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBVOCPivotFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBVOCPivotExportRequest(BaseModel):
    """Request body for a two-sheet customer-voice workbook."""

    filters: WBVOCPivotFilters = Field(default_factory=WBVOCPivotFilters)
