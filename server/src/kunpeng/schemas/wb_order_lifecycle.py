"""Schemas for the Wildberries order-item lifecycle DWM."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

LifecycleStage = Literal[
    "new",
    "assembling",
    "in_delivery",
    "wb_received",
    "ready_for_pickup",
    "sold",
    "cancelled",
    "returned",
    "unknown",
]
LifecycleAnomaly = Literal[
    "missing_current_status",
    "return_identity_conflict",
    "terminal_without_time",
]


class WBOrderLifecycleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    srid: str
    order_id: Optional[int] = None
    order_uid: Optional[str] = None
    supply_id: Optional[str] = None
    sticker_id: Optional[str] = None
    g_number: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    barcode: Optional[str] = None
    product_title: Optional[str] = None
    product_title_cn: Optional[str] = None
    subject_name: Optional[str] = None
    subject_name_cn: Optional[str] = None
    tech_size: Optional[str] = None
    tech_size_cn: Optional[str] = None
    delivery_type: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_name_cn: Optional[str] = None
    country_name: Optional[str] = None
    country_name_cn: Optional[str] = None
    region_name: Optional[str] = None
    region_name_cn: Optional[str] = None
    total_price: Optional[Decimal] = None
    price_with_disc: Optional[Decimal] = None
    finished_price: Optional[Decimal] = None
    converted_price: Optional[Decimal] = None
    currency_code: Optional[int] = None
    order_at: datetime
    last_change_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    supplier_status: Optional[str] = None
    supplier_status_cn: Optional[str] = None
    wb_status: Optional[str] = None
    wb_status_cn: Optional[str] = None
    lifecycle_stage: str
    lifecycle_stage_cn: str
    is_cancelled: bool
    is_sold: bool
    is_terminal: bool
    supply_name: Optional[str] = None
    supply_is_done: Optional[bool] = None
    supply_created_at: Optional[datetime] = None
    supply_scan_at: Optional[datetime] = None
    supply_closed_at: Optional[datetime] = None
    supply_rejected_at: Optional[datetime] = None
    sale_at: Optional[datetime] = None
    sale_last_change_at: Optional[datetime] = None
    sale_id: Optional[str] = None
    sale_event_type: Optional[str] = None
    finance_row_cnt: int = 0
    finance_sale_row_cnt: int = 0
    finance_first_sale_at: Optional[datetime] = None
    return_cnt: int = 0
    latest_return_srid: Optional[str] = None
    latest_return_order_id: Optional[int] = None
    latest_return_status: Optional[str] = None
    latest_return_status_cn: Optional[str] = None
    latest_return_type: Optional[str] = None
    latest_return_type_cn: Optional[str] = None
    latest_return_reason: Optional[str] = None
    latest_return_reason_cn: Optional[str] = None
    return_ready_at: Optional[datetime] = None
    return_completed_at: Optional[datetime] = None
    return_expired_at: Optional[datetime] = None
    return_link_method: Optional[str] = None
    has_return_identity_conflict: bool
    has_statistics_order_data: bool
    has_marketplace_order_data: bool
    has_supply_data: bool
    has_sale_data: bool
    has_finance_data: bool
    has_return_data: bool
    create_time: datetime
    update_time: Optional[datetime] = None


class WBOrderLifecycleFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    srid: Optional[str] = None
    order_id: Optional[int] = None
    supply_id: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    supplier_status: Optional[str] = None
    wb_status: Optional[str] = None
    return_status: Optional[str] = None
    return_reason: Optional[str] = None
    keyword: Optional[str] = None
    stage: Optional[LifecycleStage] = None
    anomaly: Optional[LifecycleAnomaly] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "WBOrderLifecycleFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class WBOrderLifecycleKey(BaseModel):
    shop_id: int
    srid: str


class WBOrderLifecycleExportRequest(BaseModel):
    scope: Literal["filtered", "selected"]
    filters: WBOrderLifecycleFilters = Field(default_factory=WBOrderLifecycleFilters)
    selected_keys: list[WBOrderLifecycleKey] = Field(
        default_factory=list,
        max_length=5000,
    )

    @model_validator(mode="after")
    def validate_selected(self) -> "WBOrderLifecycleExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条订单生命周期记录")
        return self


class WBOrderLifecycleMetrics(BaseModel):
    order_count: int = 0
    sold_count: int = 0
    sold_rate: float = 0
    cancelled_count: int = 0
    cancelled_rate: float = 0
    returned_count: int = 0
    returned_rate: float = 0
    terminal_count: int = 0
    marketplace_covered_count: int = 0


class WBOrderLifecycleStageItem(BaseModel):
    stage: str
    label: str
    order_count: int


class WBOrderLifecycleTrendPoint(BaseModel):
    stat_date: date
    order_count: int = 0
    sold_count: int = 0
    cancelled_count: int = 0
    returned_count: int = 0


class WBOrderLifecycleStatusItem(BaseModel):
    wb_status: Optional[str] = None
    wb_status_cn: Optional[str] = None
    order_count: int = 0


class WBOrderLifecycleSummary(BaseModel):
    metrics: WBOrderLifecycleMetrics
    stages: list[WBOrderLifecycleStageItem] = Field(default_factory=list)
    trend: list[WBOrderLifecycleTrendPoint] = Field(default_factory=list)
    statuses: list[WBOrderLifecycleStatusItem] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
