"""
ODS 层 - Wildberries 新订单（待处理组装订单）数据 CRUD
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.new_orders import ODSWBNewOrder

logger = logging.getLogger(__name__)


def safe_decimal(value: Any) -> Optional[Decimal]:
    """安全转换为 Decimal"""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """安全转换为 int"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_datetime(value: Any) -> Optional[datetime]:
    """安全转换为 datetime (处理 ISO8601 格式)"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # 处理 '2026-03-23T10:26:17Z' 格式
        if isinstance(value, str) and value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class CRUDODSWBNewOrder:
    """ODS 层 Wildberries 新订单 CRUD（只 upsert，不删除，保留 first_seen_at）"""

    async def get_by_order_id(
        self,
        db: AsyncSession,
        shop_id: int,
        order_id: int,
    ) -> Optional[ODSWBNewOrder]:
        """根据订单ID获取记录"""
        result = await db.execute(
            select(ODSWBNewOrder).where(
                and_(
                    ODSWBNewOrder.shop_id == shop_id,
                    ODSWBNewOrder.order_id == order_id,
                )
            )
        )
        return result.scalars().first()

    def _extract_fields(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """从 API 响应提取展开字段（camelCase -> snake_case）"""
        return {
            "order_uid": order_data.get("orderUid"),
            "rid": order_data.get("rid"),
            "delivery_type": order_data.get("deliveryType"),
            "created_at": safe_datetime(order_data.get("createdAt")),
            "article": order_data.get("article"),
            "nm_id": safe_int(order_data.get("nmId")),
            "chrt_id": safe_int(order_data.get("chrtId")),
            "color_code": order_data.get("colorCode"),
            "price": safe_decimal(order_data.get("price")),
            "converted_price": safe_decimal(order_data.get("convertedPrice")),
            "currency_code": safe_int(order_data.get("currencyCode")),
            "converted_currency_code": safe_int(
                order_data.get("convertedCurrencyCode")
            ),
            "sale_price": safe_decimal(order_data.get("salePrice")),
            "scan_price": safe_decimal(order_data.get("scanPrice")),
            "warehouse_id": safe_int(order_data.get("warehouseId")),
            "office_id": safe_int(order_data.get("officeId")),
            "cargo_type": safe_int(order_data.get("cargoType")),
            "ddate": order_data.get("ddate"),
            "seller_date": order_data.get("sellerDate"),
            "comment": order_data.get("comment"),
            "address": order_data.get("address"),
            "offices": order_data.get("offices"),
            "skus": order_data.get("skus"),
            "required_meta": order_data.get("requiredMeta"),
            "optional_meta": order_data.get("optionalMeta"),
            "options": order_data.get("options"),
        }

    async def create_or_update(
        self,
        db: AsyncSession,
        order_data: Dict[str, Any],
        shop_id: int,
    ) -> ODSWBNewOrder:
        """创建或更新新订单记录（保留首次入库时间 first_seen_at）"""
        order_id = safe_int(order_data.get("id"))
        fields = self._extract_fields(order_data)

        existing = await self.get_by_order_id(db, shop_id, order_id)

        if existing:
            # 更新展开字段与原始数据，但不覆盖 first_seen_at
            existing.row_data = order_data
            for key, value in fields.items():
                setattr(existing, key, value)
            await db.commit()
            await db.refresh(existing)
            logger.debug(f"[ODS CRUD] 更新新订单: order_id={order_id}")
            return existing

        db_order = ODSWBNewOrder(
            shop_id=shop_id,
            row_data=order_data,
            order_id=order_id,
            **fields,
        )
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        logger.debug(f"[ODS CRUD] 创建新订单: order_id={order_id}")
        return db_order

    async def create_many(
        self,
        db: AsyncSession,
        orders_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBNewOrder]:
        """批量创建或更新新订单记录"""
        results = []
        for order_data in orders_data:
            try:
                db_order = await self.create_or_update(db, order_data, shop_id)
                results.append(db_order)
            except Exception as e:
                logger.error(f"[ODS CRUD] 处理新订单失败: {e}")
                continue
        logger.info(f"[ODS CRUD] 新订单批量处理完成: {len(results)} 条")
        return results


crud_ods_wb_new_order = CRUDODSWBNewOrder()
