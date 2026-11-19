"""Wildberries 财务报告周明细查询与导出服务。"""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.finance import (
    DWD_BUSINESS_FIELDS,
    crud_dwd_wb_sales_report_detail,
)
from kunpeng.models.dwd.wildberries.finance import DWDWBSalesReportDetail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wildberries import WBFinancialReportDetailItem
from kunpeng.services.wb_sales_funnel_service import build_xlsx

FINANCIAL_REPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    *tuple(
        (
            DWDWBSalesReportDetail.__table__.columns[field].comment or field,
            field,
        )
        for field in DWD_BUSINESS_FIELDS
    ),
)


class WBFinancialReportService:
    """编排 DWD 财务明细查询及 Excel 生成。"""

    async def list_report_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        **filters: Any,
    ) -> PageResponse[WBFinancialReportDetailItem]:
        records, total = await crud_dwd_wb_sales_report_detail.list_report_details(
            db,
            shop_id=shop_id,
            page=page,
            page_size=page_size,
            **filters,
        )
        items = [
            WBFinancialReportDetailItem.model_validate(record) for record in records
        ]
        return PageResponse[WBFinancialReportDetailItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_report_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        **filters: Any,
    ) -> bytes:
        records = await crud_dwd_wb_sales_report_detail.list_report_details_for_export(
            db,
            shop_id=shop_id,
            **filters,
        )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=[shop_id])
        rows = []
        for record in records:
            row = {
                field: getattr(record, field, None)
                for _, field in FINANCIAL_REPORT_COLUMNS
            }
            row["shop_name"] = shop_names.get(record.shop_id)
            rows.append(row)
        return build_xlsx(
            FINANCIAL_REPORT_COLUMNS,
            rows,
            sheet_name="财务报告周明细",
        )

    @staticmethod
    def export_filename(date_from: date | None, date_to: date | None) -> str:
        start = date_from.isoformat() if date_from else "all"
        end = date_to.isoformat() if date_to else "all"
        return f"wb_financial_report_{start}_{end}.xlsx"


wb_financial_report_service = WBFinancialReportService()
