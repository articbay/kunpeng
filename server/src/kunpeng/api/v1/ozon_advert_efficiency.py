"""Ozon advertising efficiency analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_advert_efficiency import (
    OzonAdvertEfficiencyExportRequest,
    OzonAdvertEfficiencyFilters,
    OzonAdvertEfficiencyItem,
)
from kunpeng.services.ozon_advert_efficiency_service import (
    ozon_advert_efficiency_service,
)
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon广告效率"])


@router.get("/advert-efficiency", response_model=PageResponse[OzonAdvertEfficiencyItem])
async def list_advert_efficiency(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sku: Optional[int] = None,
    campaign_id: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[OzonAdvertEfficiencyItem]:
    filters = OzonAdvertEfficiencyFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        sku=sku,
        campaign_id=campaign_id,
        keyword=keyword,
        sort_order=sort_order,
    )
    return await ozon_advert_efficiency_service.list_items(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/advert-efficiency/export")
async def export_advert_efficiency(
    export_request: OzonAdvertEfficiencyExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = await ozon_advert_efficiency_service.export_items(
        db, user_id=current_user.id, request=export_request
    )
    filename = f"Ozon广告效率_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="ozon_advert_efficiency.xlsx"; '
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
