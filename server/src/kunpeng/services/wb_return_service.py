"""Wildberries return listing and export service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.return_detail import crud_dwd_wb_return_detail
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wb_return import (
    WBReturnExportRequest,
    WBReturnFilters,
    WBReturnItem,
)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

RETURN_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("品牌", "brand"),
    ("商品品类", "subject_name"),
    ("商品品类（中文）", "subject_name_cn"),
    ("原生条形码", "barcode_ori"),
    ("手调条形码", "barcode_hand"),
    ("WB商品ID", "nm_id"),
    ("标签ID", "sticker_id"),
    ("状态", "status"),
    ("状态（中文）", "status_cn"),
    ("准备好取货时间（莫斯科）", "ready_to_return_dt"),
    ("已被领取时间（莫斯科）", "completed_dt"),
    ("过期时间（莫斯科）", "expired_dt"),
    ("退货类型", "return_type"),
    ("退货类型（中文）", "return_type_cn"),
    ("下单日期", "order_dt"),
    ("退货原因", "reason"),
    ("退货原因（中文）", "reason_cn"),
    ("配货单号", "order_id"),
    ("系统订单号", "srid"),
    ("地址", "dst_office_address"),
    ("地址（中文）", "dst_office_address_cn"),
    ("地址ID", "dst_office_id"),
)


class WBReturnService:
    """Coordinate authorization, DWD queries, timezone handling and export."""

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )

    def _query_kwargs(
        self,
        filters: WBReturnFilters,
        *,
        allowed_shop_ids: list[int],
    ) -> dict:
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "nm_id": filters.nm_id,
            "order_id": filters.order_id,
            "brand": filters.brand,
            "subject_name": filters.subject_name,
            "status": filters.status,
            "return_type": filters.return_type,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_returns(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: WBReturnFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[WBReturnItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_wb_return_detail.list_returns(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[WBReturnItem](
            items=[WBReturnItem.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_returns(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBReturnExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_wb_return_detail.list_returns_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            records = await crud_dwd_wb_return_detail.list_returns_for_export(
                db,
                **self._query_kwargs(
                    export_request.filters,
                    allowed_shop_ids=allowed_shop_ids,
                ),
            )

        items = [WBReturnItem.model_validate(record) for record in records]
        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)
        rows = []
        datetime_fields = (
            "ready_to_return_dt",
            "completed_dt",
            "expired_dt",
        )
        for item in items:
            row = item.model_dump(mode="python")
            row["shop_name"] = shop_names.get(item.shop_id)
            for field in datetime_fields:
                value = getattr(item, field)
                if value:
                    row[field] = value.strftime("%Y-%m-%d %H:%M:%S")
            if item.order_dt:
                row["order_dt"] = item.order_dt.isoformat()
            rows.append(row)
        return build_xlsx(RETURN_EXPORT_COLUMNS, rows, sheet_name="WB退货")


wb_return_service = WBReturnService()
