"""Schemas for the Ozon order-product lifecycle DWM."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OzonOrderLifecycleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shop_id: int
    fulfillment_type: str
    posting_number: str
    sku: int
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    offer_id: Optional[str] = None
    product_name: Optional[str] = None
    product_name_cn: Optional[str] = None
    quantity: Optional[int] = None
    status_code: Optional[str] = None
    substatus_code: Optional[str] = None
    status_name_cn: Optional[str] = None
    in_process_at: Optional[datetime] = None
    shipment_date: Optional[datetime] = None
    transferred_to_delivery_at: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    promised_delivery_at: Optional[datetime] = None
    cancellation_at: Optional[datetime] = None
    return_cnt: int
    return_qty: int
    first_return_date: Optional[datetime] = None
    latest_return_id: Optional[int] = None
    latest_return_status_sys_name: Optional[str] = None
    latest_return_status_display_name_cn: Optional[str] = None
    latest_return_status_change_at: Optional[datetime] = None
    latest_return_reason_name_cn: Optional[str] = None
    last_ready_to_pickup_at: Optional[datetime] = None
    last_picked_up_at: Optional[datetime] = None
    create_time: datetime
    update_time: Optional[datetime] = None


LifecycleStage = Literal[
    "pending_shipment",
    "shipped",
    "transferred",
    "delivery_node",
    "cancelled",
    "returned",
]
LifecycleAnomaly = Literal[
    "promise_passed_without_delivery_node",
    "return_qty_exceeds_ordered",
    "return_status_missing",
]


class OzonOrderLifecycleFilters(BaseModel):
    shop_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    fulfillment_type: Optional[Literal["FBS", "FBO"]] = None
    posting_number: Optional[str] = None
    order_number: Optional[str] = None
    sku: Optional[int] = None
    offer_id: Optional[str] = None
    status_code: Optional[str] = None
    substatus_code: Optional[str] = None
    return_status: Optional[str] = None
    return_reason: Optional[str] = None
    keyword: Optional[str] = None
    stage: Optional[LifecycleStage] = None
    anomaly: Optional[LifecycleAnomaly] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def validate_date_range(self) -> "OzonOrderLifecycleFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class OzonOrderLifecycleKey(BaseModel):
    shop_id: int
    fulfillment_type: Literal["FBS", "FBO"]
    posting_number: str
    sku: int


class OzonOrderLifecycleExportRequest(BaseModel):
    scope: Literal["filtered", "selected"]
    filters: OzonOrderLifecycleFilters = Field(
        default_factory=OzonOrderLifecycleFilters
    )
    selected_keys: list[OzonOrderLifecycleKey] = Field(
        default_factory=list, max_length=5000
    )

    @model_validator(mode="after")
    def validate_selected(self) -> "OzonOrderLifecycleExportRequest":
        if self.scope == "selected" and not self.selected_keys:
            raise ValueError("导出已选记录时至少需要选择一条订单生命周期记录")
        return self


class OzonOrderLifecycleMetrics(BaseModel):
    posting_count: int = 0
    item_row_count: int = 0
    order_qty: int = 0
    shipped_posting_count: int = 0
    shipped_rate: float = 0
    cancelled_posting_count: int = 0
    cancelled_rate: float = 0
    returned_item_count: int = 0
    returned_item_rate: float = 0
    return_qty: int = 0


class OzonOrderLifecycleStageItem(BaseModel):
    stage: str
    label: str
    posting_count: int


class OzonOrderLifecycleTrendPoint(BaseModel):
    stat_date: date
    posting_count: int = 0
    order_qty: int = 0
    cancelled_posting_count: int = 0
    return_qty: int = 0


class OzonOrderLifecycleStatusItem(BaseModel):
    status_code: Optional[str] = None
    status_name_cn: Optional[str] = None
    posting_count: int = 0


class OzonOrderLifecycleSummary(BaseModel):
    metrics: OzonOrderLifecycleMetrics
    stages: list[OzonOrderLifecycleStageItem] = Field(default_factory=list)
    trend: list[OzonOrderLifecycleTrendPoint] = Field(default_factory=list)
    statuses: list[OzonOrderLifecycleStatusItem] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
