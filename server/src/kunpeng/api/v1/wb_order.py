"""Wildberries order analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_order import WBOrderExportRequest, WBOrderFilters, WBOrderItem
from kunpeng.services.wb_order_service import wb_order_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries订单"])


@router.get("/orders", response_model=PageResponse[WBOrderItem])
async def list_orders(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    order_id: Optional[int] = None,
    supply_id: Optional[str] = None,
    sticker_id: Optional[str] = None,
    nm_id: Optional[int] = None,
    supplier_article: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    wb_status: Optional[str] = None,
    supplier_status: Optional[str] = None,
    delivery_type: Optional[str] = None,
    is_cancellable: Optional[bool] = None,
    is_b2b: Optional[bool] = None,
    is_zero_order: Optional[bool] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBOrderItem]:
    """Page through the current user's Wildberries order rows."""
    filters = WBOrderFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        order_id=order_id,
        supply_id=supply_id,
        sticker_id=sticker_id,
        nm_id=nm_id,
        supplier_article=supplier_article,
        warehouse_id=warehouse_id,
        wb_status=wb_status,
        supplier_status=supplier_status,
        delivery_type=delivery_type,
        is_cancellable=is_cancellable,
        is_b2b=is_b2b,
        is_zero_order=is_zero_order,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await wb_order_service.list_orders(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/orders/export")
async def export_orders(
    export_request: WBOrderExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all filtered rows or the selected composite keys to Excel."""
    content = await wb_order_service.export_orders(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB履约订单_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_orders.xlsx"; ' f"filename*=UTF-8''{quote(filename)}"
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
