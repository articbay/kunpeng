"""Wildberries voice-of-customer question API."""

from datetime import date
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_voc_question import (AnswerStatus,
                                             WBVOCQuestionExportRequest,
                                             WBVOCQuestionFilters,
                                             WBVOCQuestionItem)
from kunpeng.services.wb_voc_question_service import wb_voc_question_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries客户声音"])


@router.get("/questions", response_model=PageResponse[WBVOCQuestionItem])
async def list_questions(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    supplier_article: Optional[str] = None,
    nm_id: Optional[int] = None,
    brand_name: Optional[str] = None,
    keyword: Optional[str] = None,
    answer_status: Optional[AnswerStatus] = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBVOCQuestionItem]:
    """Page through the current user's Wildberries question rows."""
    filters = WBVOCQuestionFilters(
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        supplier_article=supplier_article,
        nm_id=nm_id,
        brand_name=brand_name,
        keyword=keyword,
        answer_status=answer_status,
        sort_order=sort_order,
    )
    return await wb_voc_question_service.list_questions(
        db,
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/questions/export")
async def export_questions(
    export_request: WBVOCQuestionExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all filtered rows or the selected composite keys to Excel."""
    content = await wb_voc_question_service.export_questions(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB客户提问_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_questions.xlsx"; '
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
