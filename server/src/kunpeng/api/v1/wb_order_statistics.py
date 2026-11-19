"""Wildberries statistics-order analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order_statistics import (
    WBOrderStatisticsExportRequest,
    WBOrderStatisticsFilters,
    WBOrderStatisticsItem,
)
from kunpeng.services.wb_order_statistics_service import wb_order_statistics_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries统计订单"])


@router.get(
    "/order-statistics",
    response_model=PageResponse[WBOrderStatisticsItem],
)
async def list_order_statistics(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    srid: Optional[str] = None,
    warehouse_name: Optional[str] = None,
    country_name: Optional[str] = None,
    oblast_okrug_name: Optional[str] = None,
    region_name: Optional[str] = None,
    supplier_article: Optional[str] = None,
    nm_id: Optional[int] = None,
    category: Optional[str] = None,
    subject_name: Optional[str] = None,
    is_cancel: Optional[bool] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBOrderStatisticsItem]:
    """Page through the current user's statistics-order rows."""
    filters = WBOrderStatisticsFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        srid=srid,
        warehouse_name=warehouse_name,
        country_name=country_name,
        oblast_okrug_name=oblast_okrug_name,
        region_name=region_name,
        supplier_article=supplier_article,
        nm_id=nm_id,
        category=category,
        subject_name=subject_name,
        is_cancel=is_cancel,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await wb_order_statistics_service.list_orders(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/order-statistics/export")
async def export_order_statistics(
    export_request: WBOrderStatisticsExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export filtered or selected statistics-order rows."""
    content = await wb_order_statistics_service.export_orders(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB统计订单_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_order_statistics.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": content_disposition,
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
