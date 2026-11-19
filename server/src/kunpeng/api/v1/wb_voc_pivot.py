"""Wildberries customer-voice native PivotTable export API."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.wb_voc_pivot import WBVOCPivotExportRequest
from kunpeng.services.wb_voc_pivot_service import wb_voc_pivot_service
from kunpeng.utils.timezone import now_platform

router = APIRouter(tags=["Wildberries客户声音"])


@router.post("/pivot/export")
async def export_customer_voice_pivot(
    export_request: WBVOCPivotExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Build an XLSX from three existing DWD tables without database writes."""
    content = await wb_voc_pivot_service.export_workbook(
        db,
        user_id=current_user.id,
        export_request=export_request,
    )
    filename = f"WB客户声音分析_{now_platform().strftime('%Y%m%d_%H%M%S')}.xlsx"
    content_disposition = (
        'attachment; filename="wb_customer_voice.xlsx"; '
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
