"""Ozon order lifecycle API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_order_lifecycle import (
    LifecycleAnomaly,
    LifecycleStage,
    OzonOrderLifecycleExportRequest,
    OzonOrderLifecycleFilters,
    OzonOrderLifecycleItem,
    OzonOrderLifecycleSummary,
)
from kunpeng.services.ozon_order_lifecycle_service import ozon_order_lifecycle_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon订单生命周期"])


def _filters(**kwargs) -> OzonOrderLifecycleFilters:
    return OzonOrderLifecycleFilters(**kwargs)


@router.get("/order-lifecycle", response_model=PageResponse[OzonOrderLifecycleItem])
async def list_items(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    fulfillment_type: Optional[Literal["FBS", "FBO"]] = None,
    posting_number: Optional[str] = None,
    order_number: Optional[str] = None,
    sku: Optional[int] = None,
    offer_id: Optional[str] = None,
    status_code: Optional[str] = None,
    substatus_code: Optional[str] = None,
    return_status: Optional[str] = None,
    return_reason: Optional[str] = None,
    keyword: Optional[str] = None,
    stage: Optional[LifecycleStage] = None,
    anomaly: Optional[LifecycleAnomaly] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _filters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        fulfillment_type=fulfillment_type,
        posting_number=posting_number,
        order_number=order_number,
        sku=sku,
        offer_id=offer_id,
        status_code=status_code,
        substatus_code=substatus_code,
        return_status=return_status,
        return_reason=return_reason,
        keyword=keyword,
        stage=stage,
        anomaly=anomaly,
        sort_order=sort_order,
    )
    return await ozon_order_lifecycle_service.list_items(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.get("/order-lifecycle/summary", response_model=OzonOrderLifecycleSummary)
async def get_summary(
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    fulfillment_type: Optional[Literal["FBS", "FBO"]] = None,
    posting_number: Optional[str] = None,
    order_number: Optional[str] = None,
    sku: Optional[int] = None,
    offer_id: Optional[str] = None,
    status_code: Optional[str] = None,
    substatus_code: Optional[str] = None,
    return_status: Optional[str] = None,
    return_reason: Optional[str] = None,
    keyword: Optional[str] = None,
    stage: Optional[LifecycleStage] = None,
    anomaly: Optional[LifecycleAnomaly] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _filters(
        **{
            key: value
            for key, value in locals().items()
            if key in OzonOrderLifecycleFilters.model_fields
        }
    )
    return await ozon_order_lifecycle_service.summary(
        db, user_id=current_user.id, filters=filters
    )


@router.post("/order-lifecycle/export")
async def export_items(
    request: OzonOrderLifecycleExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = await ozon_order_lifecycle_service.export_items(
        db, user_id=current_user.id, request=request
    )
    filename = f"Ozon订单生命周期_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    disposition = (
        'attachment; filename="ozon_order_lifecycle.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": disposition,
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
