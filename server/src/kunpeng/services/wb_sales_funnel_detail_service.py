"""Wildberries DWD 销售漏斗商品明细查询与导出服务。"""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.funnel import crud_dwd_wb_sales_funnel_detail
from kunpeng.models.dwd.wildberries.funnel import DWDWBSalesFunnelDetail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wildberries import WBSalesFunnelDetailItem
from kunpeng.services.wb_sales_funnel_service import build_xlsx

EXPORT_COLUMN_LABELS = {
    "date_to": "统计结束日期",
}

_SALES_FUNNEL_DETAIL_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    (
        EXPORT_COLUMN_LABELS.get(column.name, column.comment or column.name),
        column.name,
    )
    for column in DWDWBSalesFunnelDetail.__table__.columns
    if column.name not in {"id", "source_ods_id"}
)
SALES_FUNNEL_DETAIL_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    column
    for item in _SALES_FUNNEL_DETAIL_COLUMNS
    for column in (
        (item, ("店铺名称", "shop_name")) if item[1] == "shop_id" else (item,)
    )
)


class WBSalesFunnelDetailService:
    """编排 DWD 销售漏斗明细查询及 Excel 生成。"""

    async def list_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        **filters: Any,
    ) -> PageResponse[WBSalesFunnelDetailItem]:
        records, total = await crud_dwd_wb_sales_funnel_detail.list_details(
            db,
            shop_id=shop_id,
            page=page,
            page_size=page_size,
            **filters,
        )
        items = [WBSalesFunnelDetailItem.model_validate(record) for record in records]
        return PageResponse[WBSalesFunnelDetailItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        **filters: Any,
    ) -> bytes:
        records = await crud_dwd_wb_sales_funnel_detail.list_details_for_export(
            db,
            shop_id=shop_id,
            **filters,
        )
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=[shop_id])
        rows = []
        for record in records:
            row = {
                field: getattr(record, field, None)
                for _, field in SALES_FUNNEL_DETAIL_COLUMNS
            }
            row["shop_name"] = shop_names.get(record.shop_id)
            rows.append(row)
        return build_xlsx(
            SALES_FUNNEL_DETAIL_COLUMNS,
            rows,
            sheet_name="销售漏斗明细",
        )

    @staticmethod
    def export_filename(date_from: date | None, date_to: date | None) -> str:
        start = date_from.isoformat() if date_from else "all"
        end = date_to.isoformat() if date_to else "all"
        return f"wb_sales_funnel_{start}_{end}.xlsx"


wb_sales_funnel_detail_service = WBSalesFunnelDetailService()
