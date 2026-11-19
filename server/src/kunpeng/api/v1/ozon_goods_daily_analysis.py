"""Ozon goods daily analysis API."""

from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_goods_daily_analysis import (
    GoodsAnomaly,
    GoodsDataStatus,
    OzonGoodsDailyExportRequest,
    OzonGoodsDailyFilters,
    OzonGoodsDailyItem,
    OzonGoodsDailySummary,
    OzonGoodsProductDetail,
)
from kunpeng.services.ozon_goods_daily_analysis_service import (
    ozon_goods_daily_analysis_service,
)
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Ozon商品日分析"])


def _filters(
    shop_id: int | None,
    date_from: date | None,
    date_to: date | None,
    sku: int | None,
    offer_id: str | None,
    keyword: str | None,
    data_status: GoodsDataStatus | None,
    anomaly: GoodsAnomaly | None,
    sort_order: Literal["asc", "desc"],
) -> OzonGoodsDailyFilters:
    return OzonGoodsDailyFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        sku=sku,
        offer_id=offer_id,
        keyword=keyword,
        data_status=data_status,
        anomaly=anomaly,
        sort_order=sort_order,
    )


@router.get("/goods-daily-analysis", response_model=PageResponse[OzonGoodsDailyItem])
async def list_items(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sku: Optional[int] = None,
    offer_id: Optional[str] = None,
    keyword: Optional[str] = None,
    data_status: Optional[GoodsDataStatus] = None,
    anomaly: Optional[GoodsAnomaly] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ozon_goods_daily_analysis_service.list_items(
        db,
        user_id=current_user.id,
        filters=_filters(
            shop_id,
            date_from,
            date_to,
            sku,
            offer_id,
            keyword,
            data_status,
            anomaly,
            sort_order,
        ),
        page=page,
        page_size=page_size,
    )


@router.get("/goods-daily-analysis/summary", response_model=OzonGoodsDailySummary)
async def get_summary(
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sku: Optional[int] = None,
    offer_id: Optional[str] = None,
    keyword: Optional[str] = None,
    data_status: Optional[GoodsDataStatus] = None,
    anomaly: Optional[GoodsAnomaly] = None,
    ranking_metric: Literal[
        "sales_amount", "order_qty", "ad_spend", "ad_roas", "return_rate"
    ] = "sales_amount",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ozon_goods_daily_analysis_service.summary(
        db,
        user_id=current_user.id,
        filters=_filters(
            shop_id,
            date_from,
            date_to,
            sku,
            offer_id,
            keyword,
            data_status,
            anomaly,
            "desc",
        ),
        ranking_metric=ranking_metric,
    )


@router.get(
    "/goods-daily-analysis/products/{sku}", response_model=OzonGoodsProductDetail
)
async def get_product_detail(
    sku: int,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    offer_id: Optional[str] = None,
    keyword: Optional[str] = None,
    data_status: Optional[GoodsDataStatus] = None,
    anomaly: Optional[GoodsAnomaly] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ozon_goods_daily_analysis_service.product_detail(
        db,
        user_id=current_user.id,
        sku=sku,
        filters=_filters(
            shop_id,
            date_from,
            date_to,
            None,
            offer_id,
            keyword,
            data_status,
            anomaly,
            "desc",
        ),
    )


@router.post("/goods-daily-analysis/export")
async def export_items(
    request: OzonGoodsDailyExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = await ozon_goods_daily_analysis_service.export_items(
        db, user_id=current_user.id, request=request
    )
    filename = f"Ozon商品日分析_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    disposition = (
        'attachment; filename="ozon_goods_daily_analysis.xlsx"; '
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
