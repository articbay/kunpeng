"""Wildberries voice-of-customer feedback API."""

from datetime import date
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_voc_feedback import (AnswerStatus,
                                             WBVOCFeedbackExportRequest,
                                             WBVOCFeedbackFilters,
                                             WBVOCFeedbackItem)
from kunpeng.services.wb_voc_feedback_service import wb_voc_feedback_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries客户声音"])


@router.get("/feedbacks", response_model=PageResponse[WBVOCFeedbackItem])
async def list_feedbacks(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    product_valuations: Annotated[Optional[list[int]], Query()] = None,
    supplier_article: Optional[str] = None,
    nm_id: Optional[int] = None,
    brand_name: Optional[str] = None,
    keyword: Optional[str] = None,
    answer_status: Optional[AnswerStatus] = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBVOCFeedbackItem]:
    """Page through the current user's Wildberries feedback rows."""
    filters = WBVOCFeedbackFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        product_valuations=product_valuations or [],
        supplier_article=supplier_article,
        nm_id=nm_id,
        brand_name=brand_name,
        keyword=keyword,
        answer_status=answer_status,
        sort_order=sort_order,
    )
    return await wb_voc_feedback_service.list_feedbacks(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/feedbacks/export")
async def export_feedbacks(
    export_request: WBVOCFeedbackExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all filtered rows or the selected composite keys to Excel."""
    content = await wb_voc_feedback_service.export_feedbacks(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB客户评价_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_feedbacks.xlsx"; '
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
