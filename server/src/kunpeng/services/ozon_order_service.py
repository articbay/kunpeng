"""Ozon unified order listing and Excel export service."""

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.ozon.order_detail import _delivery_level
from kunpeng.crud.dwd.ozon.order_query import crud_dwd_ozon_order_query
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.ozon_order import (OzonOrderExportRequest,
                                        OzonOrderFilters, OzonOrderItem)
from kunpeng.services.wb_sales_funnel_service import build_xlsx

FILTERED_EXPORT_LIMIT = 50_000

ORDER_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("店铺ID", "shop_id"),
    ("店铺名称", "shop_name"),
    ("订单类型", "order_type_name"),
    ("履约方式", "fulfillment_type"),
    ("发货号码", "posting_number"),
    ("Ozon订单ID", "order_id"),
    ("订单号", "order_number"),
    ("正在处理中（月）", "in_process_month"),
    ("正在处理中（日）", "in_process_date"),
    ("正在处理中（时）", "in_process_hour"),
    ("正在处理中", "in_process_at"),
    ("发运日期", "shipment_date"),
    ("订单状态编码", "status_code"),
    ("订单子状态编码", "substatus_code"),
    ("状态", "status_name_cn"),
    ("配送日期", "delivery_date"),
    ("实际转移配送日期", "transferred_to_delivery_at"),
    ("配送用时1（小时）", "delivery_duration_1_hours"),
    ("配送用时2（小时）", "delivery_duration_2_hours"),
    ("level配送用时1", "delivery_level_1"),
    ("level配送用时2", "delivery_level_2"),
    ("发货的金额", "shipment_amount"),
    ("货件的货币代码", "shipment_currency"),
    ("商品名称", "product_name"),
    ("商品名称（中文）", "product_name_cn"),
    ("Ozon SKU", "sku"),
    ("货号", "offer_id"),
    ("您的价格", "seller_price"),
    ("商品的货币代码", "product_currency"),
    ("已由买家支付", "buyer_paid_amount"),
    ("买家货币代码", "buyer_currency"),
    ("数量", "quantity"),
    ("运费", "delivery_fee"),
    ("关联货件", "related_posting_number"),
    ("商品认购", "is_marketplace_buyout"),
    ("商品打折前的价格", "old_price"),
    ("折扣百分比", "discount_percent"),
    ("折扣（卢布）", "discount_amount"),
    ("促销活动", "promotion_actions"),
    ("商品的体积重量（公斤）", "product_volume_weight"),
    ("发运集群", "cluster_from"),
    ("配送集群", "cluster_to"),
    ("规定配送至买家的时间", "promised_delivery_at"),
    ("发运评估", "shipment_assessment"),
    ("发运的仓库（Ozon官仓）", "ozon_warehouse_name"),
    ("配送地区", "delivery_region"),
    ("配送城市", "delivery_city"),
    ("配送城市（中文）", "delivery_city_cn"),
    ("配送方式", "delivery_type"),
    ("买家细分（是否Premium）", "is_premium"),
    ("法人", "is_legal"),
    ("付款方式", "payment_type"),
    ("买家地址", "buyer_address"),
    ("买家姓名", "buyer_name"),
    ("买家的电子邮箱", "buyer_email"),
    ("收件人姓名", "addressee_name"),
    ("收件人的电话号码", "buyer_phone"),
    ("配送地址", "delivery_address"),
    ("邮政编码", "postal_code"),
    ("发运的仓库（第三方仓）", "seller_warehouse_name"),
    ("发运方法", "shipment_method"),
    ("物流公司", "logistics_company"),
    ("方式名称", "delivery_method_name"),
    ("不逾期的发运日期", "shipment_date_without_delay"),
    ("取消日期", "cancellation_at"),
    ("申报的货件总重量", "declared_total_weight"),
    ("货件的实际总重量", "actual_total_weight"),
    ("货件的总体积重量", "shipment_volume_weight"),
    ("商品颜色", "product_color"),
    ("商品尺寸", "product_size"),
)

DELIVERY_EXPORT_FIELDS = (
    "delivery_duration_1_hours",
    "delivery_duration_2_hours",
    "delivery_level_1",
    "delivery_level_2",
)

DELIVERY_LEVEL_PAIRS = (
    ("delivery_duration_1_hours", "delivery_level_1"),
    ("delivery_duration_2_hours", "delivery_level_2"),
)


class ExportLimitExceededError(ValueError):
    """Raised when a filtered export would exhaust server resources."""


class OzonOrderService:
    """Coordinate shop authorization, DWD reads and Excel export."""

    async def _allowed_shop_ids(self, db: AsyncSession, *, user_id: int) -> list[int]:
        return await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="ozon"
        )

    def _query_kwargs(
        self, filters: OzonOrderFilters, *, allowed_shop_ids: list[int]
    ) -> dict[str, Any]:
        return {
            "allowed_shop_ids": allowed_shop_ids,
            "shop_id": filters.shop_id,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "fulfillment_type": filters.fulfillment_type,
            "posting_number": filters.posting_number,
            "order_id": filters.order_id,
            "order_number": filters.order_number,
            "sku": filters.sku,
            "offer_id": filters.offer_id,
            "status_code": filters.status_code,
            "substatus_code": filters.substatus_code,
            "warehouse_name": filters.warehouse_name,
            "delivery_region": filters.delivery_region,
            "delivery_city": filters.delivery_city,
            "payment_type": filters.payment_type,
            "keyword": filters.keyword,
            "sort_order": filters.sort_order,
        }

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        filters: OzonOrderFilters,
        page: int,
        page_size: int,
    ) -> PageResponse[OzonOrderItem]:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        records, total = await crud_dwd_ozon_order_query.list_orders(
            db,
            page=page,
            page_size=page_size,
            **self._query_kwargs(filters, allowed_shop_ids=allowed_shop_ids),
        )
        return PageResponse[OzonOrderItem](
            items=[OzonOrderItem.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def export_orders(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: OzonOrderExportRequest,
    ) -> bytes:
        allowed_shop_ids = await self._allowed_shop_ids(db, user_id=user_id)
        if export_request.scope == "selected":
            records = await crud_dwd_ozon_order_query.list_orders_by_keys(
                db,
                allowed_shop_ids=allowed_shop_ids,
                keys=export_request.selected_keys,
            )
        else:
            query_kwargs = self._query_kwargs(
                export_request.filters, allowed_shop_ids=allowed_shop_ids
            )
            sort_order = query_kwargs.pop("sort_order")
            total = await crud_dwd_ozon_order_query.count_orders(db, **query_kwargs)
            if total > FILTERED_EXPORT_LIMIT:
                raise ExportLimitExceededError(
                    f"筛选结果共 {total} 行，单次最多导出 {FILTERED_EXPORT_LIMIT} 行，请缩小日期或店铺范围"
                )
            records = await crud_dwd_ozon_order_query.list_orders_for_export(
                db, sort_order=sort_order, **query_kwargs
            )

        shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)

        rows: list[dict[str, Any]] = []
        for record in records:
            row = OzonOrderItem.model_validate(record).model_dump(mode="python")
            row["shop_name"] = shop_names.get(row["shop_id"])
            for duration_field, level_field in DELIVERY_LEVEL_PAIRS:
                duration = row.get(duration_field)
                if duration is not None and row.get(level_field) in (None, "", "无"):
                    row[level_field] = _delivery_level(duration)
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(value, date):
                    row[key] = value.strftime(
                        "%Y年%m月" if key == "in_process_month" else "%Y-%m-%d"
                    )
            for field in DELIVERY_EXPORT_FIELDS:
                if row.get(field) is None:
                    row[field] = "无"
            if row.get("promotion_actions") is not None:
                row["promotion_actions"] = json.dumps(
                    row["promotion_actions"], ensure_ascii=False
                )
            rows.append(row)
        return build_xlsx(ORDER_EXPORT_COLUMNS, rows, sheet_name="Ozon统一订单")


ozon_order_service = OzonOrderService()
