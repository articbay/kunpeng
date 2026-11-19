"""Ozon customer voice analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_customer_voice import (
    OzonCustomerVoiceExportRequest,
    OzonCustomerVoiceFilters,
    OzonCustomerVoiceItem,
)
from kunpeng.services.ozon_customer_voice_service import ozon_customer_voice_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon客户声音"])


@router.get("/customer-voice", response_model=PageResponse[OzonCustomerVoiceItem])
async def list_customer_voice(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    offer_id: Optional[str] = None,
    sku: Optional[int] = None,
    rating: Annotated[Optional[int], Query(ge=1, le=5)] = None,
    order_status: Optional[str] = None,
    review_status: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[OzonCustomerVoiceItem]:
    filters = OzonCustomerVoiceFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        offer_id=offer_id,
        sku=sku,
        rating=rating,
        order_status=order_status,
        review_status=review_status,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await ozon_customer_voice_service.list_items(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/customer-voice/export")
async def export_customer_voice(
    export_request: OzonCustomerVoiceExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = await ozon_customer_voice_service.export_items(
        db, user_id=current_user.id, request=export_request
    )
    filename = f"Ozon客户声音_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="ozon_customer_voice.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": content_disposition,
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
