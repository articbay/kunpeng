from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.supplies import CRUDODSWBFbsSupply
from kunpeng.models.ods.wildberries.supplies import ODSWBFbsSupply


def test_fbs_supply_model_has_shop_supply_unique_constraint():
    assert ODSWBFbsSupply.__tablename__ == "ods_wb_order_fbs_supplies"
    constraints = {
        constraint.name
        for constraint in ODSWBFbsSupply.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_fbs_supply_shop_supply" in constraints


def test_fbs_supply_record_maps_api_fields():
    seen_at = datetime(
        2026,
        7,
        24,
        3,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )
    source = {
        "id": "WB-GI-123",
        "name": "Daily supply",
        "isB2b": True,
        "done": False,
        "createdAt": "2026-07-23T01:02:03Z",
        "closedAt": None,
        "scanDt": "2026-07-24T02:00:00Z",
        "rejectDt": "2026-07-24T02:30:00Z",
        "cargoType": 1,
        "crossBorderType": 0,
        "destinationOfficeId": 507,
        "recommendedWhId": 204,
        "isPickupPointShipmentAllowed": True,
    }

    record = CRUDODSWBFbsSupply._to_record(
        source,
        shop_id=42,
        seen_at=seen_at,
    )

    assert record is not None
    assert record["shop_id"] == 42
    assert record["supply_id"] == "WB-GI-123"
    assert record["is_b2b"] is True
    assert record["is_done"] is False
    assert record["destination_office_id"] == 507
    assert record["recommended_warehouse_id"] == 204
    assert record["is_pickup_point_shipment_allowed"] is True
    assert record["created_at"].isoformat() == "2026-07-23T01:02:03+00:00"
    assert record["rejected_at"].isoformat() == "2026-07-24T02:30:00+00:00"
    assert record["row_data"] == source
    assert record["last_seen_at"] == seen_at


@pytest.mark.asyncio
async def test_fbs_supply_upsert_uses_mysql_on_duplicate_key_update():
    db = AsyncMock()
    seen_at = datetime(
        2026,
        7,
        24,
        3,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )

    count = await CRUDODSWBFbsSupply().upsert_many(
        db,
        supplies_data=[{"id": "WB-GI-123", "name": "Daily supply"}],
        shop_id=42,
        seen_at=seen_at,
    )

    assert count == 1
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=mysql.dialect()))
    assert "ON DUPLICATE KEY UPDATE" in compiled
    assert "first_seen_at" not in compiled.split("ON DUPLICATE KEY UPDATE", 1)[1]
