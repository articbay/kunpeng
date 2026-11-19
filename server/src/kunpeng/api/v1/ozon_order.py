"""Ozon unified order analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_order import (OzonOrderExportRequest,
                                        OzonOrderFilters, OzonOrderItem)
from kunpeng.services.ozon_order_service import (ExportLimitExceededError,
                                                 ozon_order_service)
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon订单"])


@router.get("/orders", response_model=PageResponse[OzonOrderItem])
async def list_orders(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    fulfillment_type: Optional[Literal["FBS", "FBO"]] = None,
    posting_number: Optional[str] = None,
    order_id: Optional[int] = None,
    order_number: Optional[str] = None,
    sku: Optional[int] = None,
    offer_id: Optional[str] = None,
    status_code: Optional[str] = None,
    substatus_code: Optional[str] = None,
    warehouse_name: Optional[str] = None,
    delivery_region: Optional[str] = None,
    delivery_city: Optional[str] = None,
    payment_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[OzonOrderItem]:
    filters = OzonOrderFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        fulfillment_type=fulfillment_type,
        posting_number=posting_number,
        order_id=order_id,
        order_number=order_number,
        sku=sku,
        offer_id=offer_id,
        status_code=status_code,
        substatus_code=substatus_code,
        warehouse_name=warehouse_name,
        delivery_region=delivery_region,
        delivery_city=delivery_city,
        payment_type=payment_type,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await ozon_order_service.list_orders(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/orders/export")
async def export_orders(
    export_request: OzonOrderExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        content = await ozon_order_service.export_orders(
            db, user_id=current_user.id, export_request=export_request
        )
    except ExportLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    filename = f"Ozon统一订单_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="ozon_orders.xlsx"; '
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
