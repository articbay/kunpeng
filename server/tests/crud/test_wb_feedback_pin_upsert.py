from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.feedback_pins import CRUDODSWBFeedbackPin
from kunpeng.models.ods.wildberries.feedback_pins import ODSWBFeedbackPin


def test_feedback_pin_model_has_shop_pin_unique_constraint():
    assert ODSWBFeedbackPin.__tablename__ == "ods_wb_voc_feedback_pins"
    constraints = {
        constraint.name
        for constraint in ODSWBFeedbackPin.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_feedback_pin_shop_pin" in constraints


@pytest.mark.asyncio
async def test_feedback_pin_upsert_deduplicates_and_uses_mysql_atomic_upsert():
    db = AsyncMock()
    seen_at = datetime(2026, 7, 26, 3, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    count = await CRUDODSWBFeedbackPin().upsert_many(
        db,
        pins_data=[
            {
                "pinId": 100,
                "feedbackId": "feedback-1",
                "state": "pinned",
                "pinOn": "nm",
                "pinMethod": "subscription",
                "nmId": 123,
                "changeStateAt": "2026-07-25T08:00:00Z",
            },
            {
                "pinId": 100,
                "feedbackId": "feedback-1",
                "state": "unpinned",
                "unpinnedCause": "sysTariffUnpinned",
                "changeStateAt": "2026-07-25T10:00:00Z",
            },
        ],
        shop_id=7,
        seen_at=seen_at,
    )

    assert count == 1
    upsert_stmt = db.execute.await_args.args[0]
    sql = str(upsert_stmt.compile(dialect=mysql.dialect()))
    assert "ON DUPLICATE KEY UPDATE" in sql
    db.commit.assert_awaited_once()
