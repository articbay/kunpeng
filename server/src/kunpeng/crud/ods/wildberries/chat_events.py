"""Idempotent persistence for Wildberries buyers chat events."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.chat_events import ODSWBChatEvent
from kunpeng.utils.timezone import platform_tz

logger = logging.getLogger(__name__)


def parse_chat_event_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO timestamp or Unix milliseconds from a WB chat event."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            logger.warning("[ODS CRUD] 无法解析聊天事件毫秒时间戳: %s", value)
            return None
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 无法解析聊天事件时间: %s", value)
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=platform_tz())
    return parsed


def _safe_timestamp_ms(value: Any, event_at: datetime) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(event_at.timestamp() * 1000)


class CRUDODSWBChatEvent:
    """Batch upsert chat events using the ``(shop_id, event_id)`` key."""

    @staticmethod
    def _to_record(
        data: Dict[str, Any], shop_id: int, synced_at: datetime
    ) -> Optional[Dict[str, Any]]:
        event_id = data.get("eventID")
        chat_id = data.get("chatID")
        if not event_id or not chat_id:
            logger.warning("[ODS CRUD] 跳过缺少 eventID/chatID 的 Wildberries 聊天事件")
            return None

        event_at = parse_chat_event_datetime(
            data.get("addTime") or data.get("addTimestamp")
        )
        if event_at is None:
            logger.warning(
                "[ODS CRUD] 跳过缺少有效时间的 Wildberries 聊天事件: %s",
                event_id,
            )
            return None

        message = data.get("message")
        if not isinstance(message, dict):
            message = {}
        attachments = message.get("attachments")
        if not isinstance(attachments, dict):
            attachments = None
        good_card = attachments.get("goodCard") if attachments else None
        if not isinstance(good_card, dict):
            good_card = {}

        return {
            "shop_id": shop_id,
            "row_data": data,
            "event_id": str(event_id),
            "chat_id": str(chat_id),
            "event_type": data.get("eventType"),
            "sender": data.get("sender"),
            "source": data.get("source"),
            "is_new_chat": data.get("isNewChat"),
            "client_name": data.get("clientName"),
            "message_text": message.get("text"),
            "attachments": attachments,
            "nm_id": good_card.get("nmID"),
            "order_rid": good_card.get("rid"),
            "event_timestamp_ms": _safe_timestamp_ms(
                data.get("addTimestamp"), event_at
            ),
            "event_at": event_at,
            "last_synced_at": synced_at,
        }

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        events_data: List[Dict[str, Any]],
        shop_id: int,
        synced_at: datetime,
    ) -> int:
        """Insert new events and refresh mutable fields for existing events."""
        records = [
            record
            for data in events_data
            if (record := self._to_record(data, shop_id, synced_at)) is not None
        ]
        if not records:
            return 0

        stmt = insert(ODSWBChatEvent).values(records)
        upsert_stmt = stmt.on_duplicate_key_update(
            row_data=stmt.inserted.row_data,
            chat_id=stmt.inserted.chat_id,
            event_type=stmt.inserted.event_type,
            sender=stmt.inserted.sender,
            source=stmt.inserted.source,
            is_new_chat=stmt.inserted.is_new_chat,
            client_name=stmt.inserted.client_name,
            message_text=stmt.inserted.message_text,
            attachments=stmt.inserted.attachments,
            nm_id=stmt.inserted.nm_id,
            order_rid=stmt.inserted.order_rid,
            event_timestamp_ms=stmt.inserted.event_timestamp_ms,
            event_at=stmt.inserted.event_at,
            last_synced_at=stmt.inserted.last_synced_at,
            update_time=func.now(),
        )
        await db.execute(upsert_stmt)
        await db.commit()
        logger.info(
            "[ODS CRUD] Wildberries 聊天事件幂等写入完成: shop_id=%s, count=%s",
            shop_id,
            len(records),
        )
        return len(records)


crud_ods_wb_chat_event = CRUDODSWBChatEvent()
