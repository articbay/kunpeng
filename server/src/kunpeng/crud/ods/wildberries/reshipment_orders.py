"""Snapshot reconciliation for Wildberries FBS reshipment orders."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.reshipment_orders import ODSWBReshipmentOrder

logger = logging.getLogger(__name__)

ReshipmentKey = Tuple[int, str]


class CRUDODSWBReshipmentOrder:
    """Reconcile a complete API snapshot without deleting historical rows."""

    @staticmethod
    def _parse_key(data: Dict[str, Any]) -> Optional[ReshipmentKey]:
        try:
            order_id = int(data.get("orderID"))
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 跳过缺少有效orderID的重新发货订单: %s", data)
            return None
        supply_id = data.get("supplyID")
        if not supply_id:
            logger.warning("[ODS CRUD] 跳过缺少supplyID的重新发货订单: %s", data)
            return None
        return order_id, str(supply_id)

    async def reconcile_snapshot(
        self,
        db: AsyncSession,
        *,
        orders_data: List[Dict[str, Any]],
        shop_id: int,
        observed_at: datetime,
    ) -> Dict[str, int]:
        """Upsert the current snapshot and resolve active rows now absent."""
        existing_result = await db.execute(
            select(
                ODSWBReshipmentOrder.id,
                ODSWBReshipmentOrder.order_id,
                ODSWBReshipmentOrder.supply_id,
                ODSWBReshipmentOrder.is_active,
                ODSWBReshipmentOrder.first_seen_at,
                ODSWBReshipmentOrder.status_changed_at,
            ).where(ODSWBReshipmentOrder.shop_id == shop_id)
        )
        existing = {
            (int(row.order_id), str(row.supply_id)): row
            for row in existing_result.all()
        }

        current_payloads: Dict[ReshipmentKey, Dict[str, Any]] = {}
        for data in orders_data:
            if not isinstance(data, dict):
                logger.warning("[ODS CRUD] 跳过非对象重新发货订单响应: %s", data)
                continue
            key = self._parse_key(data)
            if key is not None:
                current_payloads[key] = data

        current_keys = set(current_payloads)
        existing_keys = set(existing)
        active_before = {key for key, row in existing.items() if bool(row.is_active)}
        new_keys = current_keys - existing_keys
        reactivated_keys = {
            key
            for key in current_keys & existing_keys
            if not bool(existing[key].is_active)
        }
        resolved_keys = active_before - current_keys

        records = []
        for key, data in current_payloads.items():
            order_id, supply_id = key
            previous = existing.get(key)
            records.append(
                {
                    "shop_id": shop_id,
                    "order_id": order_id,
                    "supply_id": supply_id,
                    "row_data": data,
                    "is_active": True,
                    "first_seen_at": (
                        previous.first_seen_at if previous else observed_at
                    ),
                    "last_seen_at": observed_at,
                    "status_changed_at": (
                        observed_at
                        if previous is None or not bool(previous.is_active)
                        else previous.status_changed_at
                    ),
                    "resolved_at": None,
                }
            )

        if records:
            stmt = insert(ODSWBReshipmentOrder).values(records)
            await db.execute(
                stmt.on_duplicate_key_update(
                    row_data=stmt.inserted.row_data,
                    is_active=stmt.inserted.is_active,
                    last_seen_at=stmt.inserted.last_seen_at,
                    status_changed_at=stmt.inserted.status_changed_at,
                    resolved_at=stmt.inserted.resolved_at,
                    update_time=func.now(),
                )
            )

        if resolved_keys:
            resolved_ids = [existing[key].id for key in resolved_keys]
            await db.execute(
                update(ODSWBReshipmentOrder)
                .where(ODSWBReshipmentOrder.id.in_(resolved_ids))
                .values(
                    is_active=False,
                    status_changed_at=observed_at,
                    resolved_at=observed_at,
                    update_time=func.now(),
                )
            )

        await db.commit()
        result = {
            "count": len(current_keys),
            "ods_count": len(records),
            "new_count": len(new_keys),
            "reactivated_count": len(reactivated_keys),
            "resolved_count": len(resolved_keys),
        }
        logger.info(
            "[ODS CRUD] Wildberries重新发货订单快照核对完成: shop_id=%s, %s",
            shop_id,
            result,
        )
        return result

    async def count_changed_in_window(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        """Count rows whose latest detected state change is in the window."""
        result = await db.execute(
            select(func.count(ODSWBReshipmentOrder.id)).where(
                and_(
                    ODSWBReshipmentOrder.shop_id == shop_id,
                    ODSWBReshipmentOrder.status_changed_at >= window_start,
                    ODSWBReshipmentOrder.status_changed_at < window_end,
                )
            )
        )
        return int(result.scalar_one())


crud_ods_wb_reshipment_order = CRUDODSWBReshipmentOrder()
