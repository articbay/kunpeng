from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.order_metadata import CRUDODSWBOrderMetadata
from kunpeng.models.ods.wildberries.order_metadata import ODSWBOrderMetadata


def test_order_metadata_model_has_shop_order_unique_constraint():
    constraints = {
        constraint.name
        for constraint in ODSWBOrderMetadata.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_order_metadata_shop_order" in constraints


def test_order_metadata_record_preserves_current_and_legacy_payloads():
    synced_at = datetime(
        2026,
        7,
        24,
        3,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )
    source = {
        "id": 123,
        "metaDetails": [{"key": "uin", "value": None, "decision": "uinMaySell"}],
        "meta": {"uin": {"value": "1234567890123456"}},
    }

    record = CRUDODSWBOrderMetadata._to_record(
        source,
        shop_id=42,
        synced_at=synced_at,
    )

    assert record is not None
    assert record["shop_id"] == 42
    assert record["order_id"] == 123
    assert record["meta_details"] == source["metaDetails"]
    assert record["legacy_meta"] == source["meta"]
    assert record["row_data"] == source


@pytest.mark.asyncio
async def test_order_metadata_upsert_uses_mysql_on_duplicate_key_update():
    db = AsyncMock()
    synced_at = datetime(
        2026,
        7,
        24,
        3,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )
    crud = CRUDODSWBOrderMetadata()

    count = await crud.upsert_many(
        db,
        metadata=[{"id": 123, "metaDetails": [], "meta": {}}],
        shop_id=42,
        synced_at=synced_at,
    )

    assert count == 1
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=mysql.dialect()))
    assert "ON DUPLICATE KEY UPDATE" in compiled
