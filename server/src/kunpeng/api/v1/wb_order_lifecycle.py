"""Wildberries order lifecycle API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order_lifecycle import (
    LifecycleAnomaly,
    LifecycleStage,
    WBOrderLifecycleExportRequest,
    WBOrderLifecycleFilters,
    WBOrderLifecycleItem,
    WBOrderLifecycleSummary,
)
from kunpeng.services.wb_order_lifecycle_service import (
    wb_order_lifecycle_service,
)
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["WB订单生命周期"])


def _filters(**kwargs) -> WBOrderLifecycleFilters:
    return WBOrderLifecycleFilters(**kwargs)


@router.get("/order-lifecycle", response_model=PageResponse[WBOrderLifecycleItem])
async def list_items(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    srid: Optional[str] = None,
    order_id: Optional[int] = None,
    supply_id: Optional[str] = None,
    nm_id: Optional[int] = None,
    supplier_article: Optional[str] = None,
    supplier_status: Optional[str] = None,
    wb_status: Optional[str] = None,
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
        srid=srid,
        order_id=order_id,
        supply_id=supply_id,
        nm_id=nm_id,
        supplier_article=supplier_article,
        supplier_status=supplier_status,
        wb_status=wb_status,
        return_status=return_status,
        return_reason=return_reason,
        keyword=keyword,
        stage=stage,
        anomaly=anomaly,
        sort_order=sort_order,
    )
    return await wb_order_lifecycle_service.list_items(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.get("/order-lifecycle/summary", response_model=WBOrderLifecycleSummary)
async def get_summary(
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    srid: Optional[str] = None,
    order_id: Optional[int] = None,
    supply_id: Optional[str] = None,
    nm_id: Optional[int] = None,
    supplier_article: Optional[str] = None,
    supplier_status: Optional[str] = None,
    wb_status: Optional[str] = None,
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
            if key in WBOrderLifecycleFilters.model_fields
        }
    )
    return await wb_order_lifecycle_service.summary(
        db,
        user_id=current_user.id,
        filters=filters,
    )


@router.post("/order-lifecycle/export")
async def export_items(
    request: WBOrderLifecycleExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = await wb_order_lifecycle_service.export_items(
        db,
        user_id=current_user.id,
        request=request,
    )
    filename = f"WB订单生命周期_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    disposition = (
        'attachment; filename="wb_order_lifecycle.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": disposition,
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
