"""Idempotent persistence for Wildberries FBS supplies."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.supplies import ODSWBFbsSupply
from kunpeng.utils.timezone import platform_tz

logger = logging.getLogger(__name__)


def parse_supply_datetime(value: Any) -> Optional[datetime]:
    """Parse a WB timestamp and attach the platform timezone when omitted."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 无法解析Wildberries供货单时间: %s", value)
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=platform_tz())
    return parsed


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


class CRUDODSWBFbsSupply:
    """Batch upsert supplies using the table's ``(shop_id, supply_id)`` key."""

    @staticmethod
    def _to_record(
        data: Dict[str, Any],
        *,
        shop_id: int,
        seen_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        supply_id = data.get("id")
        if not supply_id:
            logger.warning("[ODS CRUD] 跳过缺少id的Wildberries FBS供货单")
            return None

        return {
            "shop_id": shop_id,
            "supply_id": str(supply_id),
            "name": data.get("name"),
            "is_b2b": _optional_bool(data.get("isB2b")),
            "is_done": _optional_bool(data.get("done")),
            "created_at": parse_supply_datetime(data.get("createdAt")),
            "closed_at": parse_supply_datetime(data.get("closedAt")),
            "scan_at": parse_supply_datetime(data.get("scanDt")),
            "rejected_at": parse_supply_datetime(data.get("rejectDt")),
            "cargo_type": data.get("cargoType"),
            "cross_border_type": data.get("crossBorderType"),
            "destination_office_id": data.get("destinationOfficeId"),
            "recommended_warehouse_id": data.get("recommendedWhId"),
            "is_pickup_point_shipment_allowed": _optional_bool(
                data.get("isPickupPointShipmentAllowed")
            ),
            "row_data": data,
            "last_seen_at": seen_at,
        }

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        supplies_data: List[Dict[str, Any]],
        shop_id: int,
        seen_at: datetime,
    ) -> int:
        """Insert new supplies and refresh mutable fields on repeated runs."""
        records = [
            record
            for data in supplies_data
            if (
                record := self._to_record(
                    data,
                    shop_id=shop_id,
                    seen_at=seen_at,
                )
            )
            is not None
        ]
        if not records:
            return 0

        stmt = insert(ODSWBFbsSupply).values(records)
        upsert_stmt = stmt.on_duplicate_key_update(
            name=stmt.inserted.name,
            is_b2b=stmt.inserted.is_b2b,
            is_done=stmt.inserted.is_done,
            created_at=stmt.inserted.created_at,
            closed_at=stmt.inserted.closed_at,
            scan_at=stmt.inserted.scan_at,
            rejected_at=stmt.inserted.rejected_at,
            cargo_type=stmt.inserted.cargo_type,
            cross_border_type=stmt.inserted.cross_border_type,
            destination_office_id=stmt.inserted.destination_office_id,
            recommended_warehouse_id=stmt.inserted.recommended_warehouse_id,
            is_pickup_point_shipment_allowed=(
                stmt.inserted.is_pickup_point_shipment_allowed
            ),
            row_data=stmt.inserted.row_data,
            last_seen_at=stmt.inserted.last_seen_at,
            update_time=func.now(),
        )
        await db.execute(upsert_stmt)
        await db.commit()
        logger.info(
            "[ODS CRUD] Wildberries FBS供货单幂等写入完成: shop_id=%s, count=%s",
            shop_id,
            len(records),
        )
        return len(records)


crud_ods_wb_fbs_supply = CRUDODSWBFbsSupply()
