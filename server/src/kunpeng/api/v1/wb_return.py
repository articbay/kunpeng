"""Wildberries return analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_return import (
    WBReturnExportRequest,
    WBReturnFilters,
    WBReturnItem,
)
from kunpeng.services.wb_return_service import wb_return_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries退货"])


@router.get("/returns", response_model=PageResponse[WBReturnItem])
async def list_returns(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = None,
    order_id: Optional[int] = None,
    brand: Optional[str] = None,
    subject_name: Optional[str] = None,
    status: Optional[str] = None,
    return_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBReturnItem]:
    """Page through the current user's Wildberries return rows."""
    filters = WBReturnFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        order_id=order_id,
        brand=brand,
        subject_name=subject_name,
        status=status,
        return_type=return_type,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await wb_return_service.list_returns(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/returns/export")
async def export_returns(
    export_request: WBReturnExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all filtered rows or the selected composite keys to Excel."""
    content = await wb_return_service.export_returns(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB退货_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_returns.xlsx"; ' f"filename*=UTF-8''{quote(filename)}"
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
