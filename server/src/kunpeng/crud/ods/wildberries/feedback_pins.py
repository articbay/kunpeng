"""Idempotent persistence for Wildberries pinned feedback operations."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.feedback_pins import ODSWBFeedbackPin
from kunpeng.utils.timezone import platform_tz

logger = logging.getLogger(__name__)


def parse_feedback_pin_datetime(value: Any) -> Optional[datetime]:
    """Parse a WB RFC3339 timestamp and attach platform timezone if omitted."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 无法解析Wildberries评价置顶时间: %s", value)
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=platform_tz())
    return parsed


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class CRUDODSWBFeedbackPin:
    """Upsert pin operations by ``(shop_id, pin_id)``."""

    @staticmethod
    def _to_record(
        data: Dict[str, Any],
        *,
        shop_id: int,
        seen_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        pin_id = _optional_int(data.get("pinId"))
        feedback_id = data.get("feedbackId")
        state = data.get("state")
        if pin_id is None or not feedback_id or state not in {"pinned", "unpinned"}:
            logger.warning(
                "[ODS CRUD] 跳过缺少有效pinId、feedbackId或state的评价置顶记录: %s",
                data,
            )
            return None

        return {
            "shop_id": shop_id,
            "pin_id": pin_id,
            "feedback_id": str(feedback_id),
            "nm_id": _optional_int(data.get("nmId")),
            "imt_id": _optional_int(data.get("imtId")),
            "state": state,
            "pin_on": data.get("pinOn"),
            "pin_method": data.get("pinMethod"),
            "change_state_at": parse_feedback_pin_datetime(data.get("changeStateAt")),
            "unpinned_cause": data.get("unpinnedCause"),
            "row_data": data,
            "first_seen_at": seen_at,
            "last_seen_at": seen_at,
        }

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        pins_data: List[Dict[str, Any]],
        shop_id: int,
        seen_at: datetime,
    ) -> int:
        """Insert new pin operations and refresh mutable fields."""
        records_by_pin_id: Dict[int, Dict[str, Any]] = {}
        for data in pins_data:
            if not isinstance(data, dict):
                logger.warning("[ODS CRUD] 跳过非对象评价置顶响应: %s", data)
                continue
            record = self._to_record(data, shop_id=shop_id, seen_at=seen_at)
            if record is not None:
                records_by_pin_id[record["pin_id"]] = record

        records = list(records_by_pin_id.values())
        if not records:
            return 0

        stmt = insert(ODSWBFeedbackPin).values(records)
        upsert_stmt = stmt.on_duplicate_key_update(
            feedback_id=stmt.inserted.feedback_id,
            nm_id=stmt.inserted.nm_id,
            imt_id=stmt.inserted.imt_id,
            state=stmt.inserted.state,
            pin_on=stmt.inserted.pin_on,
            pin_method=stmt.inserted.pin_method,
            change_state_at=stmt.inserted.change_state_at,
            unpinned_cause=stmt.inserted.unpinned_cause,
            row_data=stmt.inserted.row_data,
            last_seen_at=stmt.inserted.last_seen_at,
            update_time=func.now(),
        )
        await db.execute(upsert_stmt)
        await db.commit()
        logger.info(
            "[ODS CRUD] Wildberries评价置顶记录幂等写入完成: shop_id=%s, count=%s",
            shop_id,
            len(records),
        )
        return len(records)


crud_ods_wb_feedback_pin = CRUDODSWBFeedbackPin()
