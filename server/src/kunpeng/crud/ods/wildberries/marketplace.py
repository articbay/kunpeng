"""
ODS 层 - Marketplace 订单数据 CRUD
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.marketplace import (
    ODSWBMarketplaceOrder,
    ODSWBMarketplaceOrderStatusHistory,
)

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
    """安全转换为 datetime (处理ISO8601格式)"""
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


class CRUDODSWBMarketplaceOrder:
    """ODS 层 Marketplace 订单 CRUD"""

    async def get_by_order_id(
        self,
        db: AsyncSession,
        shop_id: int,
        order_id: int,
    ) -> Optional[ODSWBMarketplaceOrder]:
        """根据订单ID获取记录"""
        result = await db.execute(
            select(ODSWBMarketplaceOrder).where(
                and_(
                    ODSWBMarketplaceOrder.shop_id == shop_id,
                    ODSWBMarketplaceOrder.order_id == order_id,
                )
            )
        )
        return result.scalars().first()

    async def create_or_update(
        self,
        db: AsyncSession,
        order_data: Dict[str, Any],
        shop_id: int,
    ) -> ODSWBMarketplaceOrder:
        """创建或更新订单记录"""
        # 提取关键字段
        order_id = safe_int(order_data.get("id"))
        # 检查是否已存在
        existing = await self.get_by_order_id(db, shop_id, order_id)

        if existing:
            # 更新现有记录
            existing.row_data = order_data
            existing.order_uid = order_data.get("orderUid")
            existing.rid = order_data.get("rid")
            existing.supply_id = order_data.get("supplyId")
            existing.delivery_type = order_data.get("deliveryType")
            existing.created_at = safe_datetime(order_data.get("createdAt"))
            existing.article = order_data.get("article")
            existing.nm_id = safe_int(order_data.get("nmId"))
            existing.chrt_id = safe_int(order_data.get("chrtId"))
            existing.color_code = order_data.get("colorCode")
            existing.price = safe_decimal(order_data.get("price"))
            existing.converted_price = safe_decimal(order_data.get("convertedPrice"))
            existing.currency_code = safe_int(order_data.get("currencyCode"))
            existing.converted_currency_code = safe_int(
                order_data.get("convertedCurrencyCode")
            )
            existing.scan_price = safe_decimal(order_data.get("scanPrice"))
            existing.warehouse_id = safe_int(order_data.get("warehouseId"))
            existing.office_id = safe_int(order_data.get("officeId"))
            existing.cargo_type = safe_int(order_data.get("cargoType"))
            existing.cross_border_type = safe_int(order_data.get("crossBorderType"))
            existing.is_zero_order = order_data.get("isZeroOrder")
            existing.comment = order_data.get("comment")
            existing.address = order_data.get("address")
            existing.offices = order_data.get("offices")
            existing.skus = order_data.get("skus")
            existing.options = order_data.get("options")

            # 订单状态字段（这些会从另一个API更新）
            if "isCancellable" in order_data:
                existing.is_cancellable = order_data.get("isCancellable")
            if "supplierStatus" in order_data:
                existing.supplier_status = order_data.get("supplierStatus")
            if "wbStatus" in order_data:
                existing.wb_status = order_data.get("wbStatus")

            await db.commit()
            await db.refresh(existing)
            logger.debug(f"[ODS CRUD] 更新订单: order_id={order_id}")
            return existing

        else:
            # 创建新记录
            db_order = ODSWBMarketplaceOrder(
                shop_id=shop_id,
                row_data=order_data,
                order_id=order_id,
                order_uid=order_data.get("orderUid"),
                rid=order_data.get("rid"),
                supply_id=order_data.get("supplyId"),
                delivery_type=order_data.get("deliveryType"),
                created_at=safe_datetime(order_data.get("createdAt")),
                article=order_data.get("article"),
                nm_id=safe_int(order_data.get("nmId")),
                chrt_id=safe_int(order_data.get("chrtId")),
                color_code=order_data.get("colorCode"),
                price=safe_decimal(order_data.get("price")),
                converted_price=safe_decimal(order_data.get("convertedPrice")),
                currency_code=safe_int(order_data.get("currencyCode")),
                converted_currency_code=safe_int(
                    order_data.get("convertedCurrencyCode")
                ),
                scan_price=safe_decimal(order_data.get("scanPrice")),
                warehouse_id=safe_int(order_data.get("warehouseId")),
                office_id=safe_int(order_data.get("officeId")),
                cargo_type=safe_int(order_data.get("cargoType")),
                cross_border_type=safe_int(order_data.get("crossBorderType")),
                is_zero_order=order_data.get("isZeroOrder"),
                comment=order_data.get("comment"),
                address=order_data.get("address"),
                offices=order_data.get("offices"),
                skus=order_data.get("skus"),
                options=order_data.get("options"),
                # 订单状态字段
                is_cancellable=order_data.get("isCancellable"),
                supplier_status=order_data.get("supplierStatus"),
                wb_status=order_data.get("wbStatus"),
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
    ) -> List[ODSWBMarketplaceOrder]:
        """批量创建或更新订单记录"""
        results = []

        for order_data in orders_data:
            try:
                db_order = await self.create_or_update(db, order_data, shop_id)
                results.append(db_order)
            except Exception as e:
                logger.error(f"[ODS CRUD] 处理订单失败: {e}")
                continue

        logger.info(f"[ODS CRUD] 批量处理完成: {len(results)} 条")
        return results


class CRUDODSWBMarketplaceOrderStatusHistory:
    """ODS 层 Marketplace 订单状态历史 CRUD"""

    async def get_by_order_id(
        self,
        db: AsyncSession,
        shop_id: int,
        order_id: int,
    ) -> Optional[ODSWBMarketplaceOrderStatusHistory]:
        """根据订单ID获取状态历史记录"""
        result = await db.execute(
            select(ODSWBMarketplaceOrderStatusHistory).where(
                and_(
                    ODSWBMarketplaceOrderStatusHistory.shop_id == shop_id,
                    ODSWBMarketplaceOrderStatusHistory.order_id == order_id,
                )
            )
        )
        return result.scalars().first()

    async def create_or_update(
        self,
        db: AsyncSession,
        status_history_data: Dict[str, Any],
        shop_id: int,
        order_id: int,
    ) -> ODSWBMarketplaceOrderStatusHistory:
        """创建或更新订单状态历史记录"""
        # 检查是否已存在
        existing = await self.get_by_order_id(db, shop_id, order_id)

        if existing:
            # 更新现有记录
            existing.row_data = status_history_data
            await db.commit()
            await db.refresh(existing)
            logger.debug(f"[ODS CRUD] 更新订单状态历史: order_id={order_id}")
            return existing

        else:
            # 创建新记录
            db_status_history = ODSWBMarketplaceOrderStatusHistory(
                shop_id=shop_id,
                order_id=order_id,
                row_data=status_history_data,
            )
            db.add(db_status_history)
            await db.commit()
            await db.refresh(db_status_history)
            logger.debug(f"[ODS CRUD] 创建新订单状态历史: order_id={order_id}")
            return db_status_history

    async def create_many(
        self,
        db: AsyncSession,
        orders_status_histories: Dict[int, Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBMarketplaceOrderStatusHistory]:
        """批量为多个订单创建或更新状态历史记录"""
        all_results = []

        for order_id, status_history_data in orders_status_histories.items():
            try:
                db_status_history = await self.create_or_update(
                    db, status_history_data, shop_id, order_id
                )
                all_results.append(db_status_history)
            except Exception as e:
                logger.error(f"[ODS CRUD] 处理订单状态历史失败: {e}")
                continue

        logger.info(f"[ODS CRUD] 订单状态历史批量处理完成: {len(all_results)} 条")
        return all_results


# 创建实例
crud_ods_wb_marketplace_order = CRUDODSWBMarketplaceOrder()
crud_ods_wb_marketplace_order_status_history = CRUDODSWBMarketplaceOrderStatusHistory()
