"""Wildberries DWD 财务报告周汇总查询与导出服务。"""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.sales_report_summary import (
    crud_dwd_wb_sales_report_summary,
)
from kunpeng.models.dwd.wildberries.sales_report_summary import DWDWBSalesReportSummary
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wildberries import WBSalesReportSummaryItem
from kunpeng.services.wb_sales_funnel_service import build_xlsx

_SALES_REPORT_SUMMARY_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    (column.comment or column.name, column.name)
    for column in DWDWBSalesReportSummary.__table__.columns
    if column.name not in {"id", "source_ods_id"}
)
SALES_REPORT_SUMMARY_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    column
    for item in _SALES_REPORT_SUMMARY_COLUMNS
    for column in (
        (item, ("店铺名称", "shop_name")) if item[1] == "shop_id" else (item,)
    )
)


class WBSalesReportSummaryService:
    """编排 DWD 财务报告周汇总查询及 Excel 生成。"""

    async def list_summaries(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        **filters: Any,
    ) -> PageResponse[WBSalesReportSummaryItem]:
        records, total = await crud_dwd_wb_sales_report_summary.list_summaries(
            db,
            shop_id=shop_id,
            page=page,
            page_size=page_size,
            **filters,
        )
        items = [WBSalesReportSummaryItem.model_validate(record) for record in records]
        return PageResponse[WBSalesReportSummaryItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_summaries(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        **filters: Any,
    ) -> bytes:
        records = await crud_dwd_wb_sales_report_summary.list_summaries_for_export(
            db,
            shop_id=shop_id,
            **filters,
        )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=[shop_id])
        rows = []
        for record in records:
            row = {
                field: getattr(record, field, None)
                for _, field in SALES_REPORT_SUMMARY_COLUMNS
            }
            row["shop_name"] = shop_names.get(record.shop_id)
            rows.append(row)
        return build_xlsx(
            SALES_REPORT_SUMMARY_COLUMNS,
            rows,
            sheet_name="财务报表周汇总",
        )

    @staticmethod
    def export_filename(date_from: date | None, date_to: date | None) -> str:
        start = date_from.isoformat() if date_from else "all"
        end = date_to.isoformat() if date_to else "all"
        return f"wb_financial_summary_{start}_{end}.xlsx"


wb_sales_report_summary_service = WBSalesReportSummaryService()
