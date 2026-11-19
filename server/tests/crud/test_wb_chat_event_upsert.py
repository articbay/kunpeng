from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.chat_events import CRUDODSWBChatEvent
from kunpeng.models.ods.wildberries.chat_events import ODSWBChatEvent


def test_chat_event_model_has_shop_event_unique_constraint():
    assert ODSWBChatEvent.__tablename__ == "ods_wb_voc_chat_events"
    constraints = {
        constraint.name
        for constraint in ODSWBChatEvent.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_chat_event_shop_event" in constraints


def test_chat_event_record_extracts_message_and_good_card():
    moscow = ZoneInfo("Europe/Moscow")
    synced_at = datetime(2026, 7, 24, 10, 0, tzinfo=moscow)
    source = {
        "eventID": "event-1",
        "chatID": "chat-1",
        "eventType": "message",
        "sender": "client",
        "source": "rusite",
        "isNewChat": True,
        "clientName": "Buyer",
        "addTimestamp": 1784871000000,
        "addTime": "2026-07-24T09:30:00+03:00",
        "message": {
            "text": "收到的颜色不对",
            "attachments": {"goodCard": {"nmID": 12345678, "rid": "order-rid"}},
        },
    }

    record = CRUDODSWBChatEvent._to_record(source, 42, synced_at)

    assert record is not None
    assert record["shop_id"] == 42
    assert record["event_id"] == "event-1"
    assert record["message_text"] == "收到的颜色不对"
    assert record["nm_id"] == 12345678
    assert record["order_rid"] == "order-rid"
    assert record["event_at"].tzinfo is not None
    assert record["row_data"] == source


@pytest.mark.asyncio
async def test_chat_event_upsert_uses_mysql_on_duplicate_key_update():
    db = AsyncMock()
    moscow = ZoneInfo("Europe/Moscow")
    synced_at = datetime(2026, 7, 24, 10, 0, tzinfo=moscow)
    crud = CRUDODSWBChatEvent()

    count = await crud.upsert_many(
        db,
        events_data=[
            {
                "eventID": "event-1",
                "chatID": "chat-1",
                "addTimestamp": 1784871000000,
                "addTime": "2026-07-24T09:30:00+03:00",
                "message": {"text": "您好"},
            }
        ],
        shop_id=42,
        synced_at=synced_at,
    )

    assert count == 1
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=mysql.dialect()))
    assert "ON DUPLICATE KEY UPDATE" in compiled
