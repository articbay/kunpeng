from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.return_claims import CRUDODSWBReturnClaim
from kunpeng.models.ods.wildberries.return_claims import ODSWBReturnClaim


def test_return_claim_model_has_shop_claim_unique_constraint():
    constraints = {
        constraint.name
        for constraint in ODSWBReturnClaim.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_return_claim_shop_claim" in constraints


def test_return_claim_record_maps_fields_and_keeps_raw_response_clean():
    moscow = ZoneInfo("Europe/Moscow")
    synced_at = datetime(2026, 7, 23, 10, 0, tzinfo=moscow)
    source = {
        "id": "claim-1",
        "claim_type": 1,
        "status": 2,
        "nm_id": 196320101,
        "user_comment": "尺寸不符",
        "dt": "2026-07-23T09:15:00",
        "dt_update": "2026-07-23T09:30:00",
        "price": 157,
        "_is_archive": True,
    }

    record = CRUDODSWBReturnClaim._to_record(source, 42, synced_at)

    assert record is not None
    assert record["shop_id"] == 42
    assert record["claim_id"] == "claim-1"
    assert record["is_archive"] is True
    assert record["claim_updated_at"].tzinfo == moscow
    assert "_is_archive" not in record["row_data"]
    assert str(record["price"]) == "157"


@pytest.mark.asyncio
async def test_return_claim_upsert_uses_mysql_on_duplicate_key_update():
    db = AsyncMock()
    moscow = ZoneInfo("Europe/Moscow")
    synced_at = datetime(2026, 7, 23, 10, 0, tzinfo=moscow)
    crud = CRUDODSWBReturnClaim()

    count = await crud.upsert_many(
        db,
        claims_data=[
            {
                "id": "claim-1",
                "dt_update": "2026-07-23T09:30:00",
                "_is_archive": False,
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
