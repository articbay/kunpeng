"""Ozon return analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_return import (OzonReturnExportRequest,
                                         OzonReturnFilters, OzonReturnItem)
from kunpeng.services.ozon_return_service import ozon_return_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon退货"])


@router.get("/returns", response_model=PageResponse[OzonReturnItem])
async def list_returns(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    return_id: Optional[int] = None,
    nm_id: Optional[int] = None,
    posting_number: Optional[str] = None,
    order_id: Optional[int] = None,
    order_number: Optional[str] = None,
    offer_id: Optional[str] = None,
    brand_name: Optional[str] = None,
    category_name: Optional[str] = None,
    product_name: Optional[str] = None,
    status: Optional[str] = None,
    return_type: Optional[str] = None,
    schema_name: Optional[str] = Query(default=None, alias="schema"),
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[OzonReturnItem]:
    """Page through the current user's Ozon return rows."""
    filters = OzonReturnFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        return_id=return_id,
        nm_id=nm_id,
        posting_number=posting_number,
        order_id=order_id,
        order_number=order_number,
        offer_id=offer_id,
        brand_name=brand_name,
        category_name=category_name,
        product_name=product_name,
        status=status,
        return_type=return_type,
        schema=schema_name,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await ozon_return_service.list_returns(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/returns/export")
async def export_returns(
    export_request: OzonReturnExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all filtered Ozon rows or selected composite keys to Excel."""
    content = await ozon_return_service.export_returns(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"Ozon退货_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="ozon_returns.xlsx"; '
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
