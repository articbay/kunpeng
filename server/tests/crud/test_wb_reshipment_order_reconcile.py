from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import mysql

from kunpeng.crud.ods.wildberries.reshipment_orders import CRUDODSWBReshipmentOrder
from kunpeng.models.ods.wildberries.reshipment_orders import ODSWBReshipmentOrder


def test_reshipment_model_has_shop_order_supply_unique_constraint():
    assert ODSWBReshipmentOrder.__tablename__ == "ods_wb_order_reshipment_orders"
    constraints = {
        constraint.name
        for constraint in ODSWBReshipmentOrder.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_wb_reshipment_shop_order_supply" in constraints


@pytest.mark.asyncio
async def test_reconcile_snapshot_adds_reactivates_and_resolves_atomically():
    moscow = ZoneInfo("Europe/Moscow")
    old_time = datetime(2026, 7, 22, 3, 0, tzinfo=moscow)
    observed_at = datetime(2026, 7, 24, 3, 0, tzinfo=moscow)
    active = SimpleNamespace(
        id=1,
        order_id=100,
        supply_id="WB-GI-1",
        is_active=True,
        first_seen_at=old_time,
        status_changed_at=old_time,
    )
    inactive = SimpleNamespace(
        id=2,
        order_id=200,
        supply_id="WB-GI-2",
        is_active=False,
        first_seen_at=old_time,
        status_changed_at=old_time,
    )
    existing_result = Mock()
    existing_result.all.return_value = [active, inactive]
    db = AsyncMock()
    db.execute.side_effect = [existing_result, Mock(), Mock()]

    result = await CRUDODSWBReshipmentOrder().reconcile_snapshot(
        db,
        orders_data=[
            {"orderID": 200, "supplyID": "WB-GI-2"},
            {"orderID": 300, "supplyID": "WB-GI-3"},
            {"orderID": 300, "supplyID": "WB-GI-3"},
        ],
        shop_id=7,
        observed_at=observed_at,
    )

    assert result == {
        "count": 2,
        "ods_count": 2,
        "new_count": 1,
        "reactivated_count": 1,
        "resolved_count": 1,
    }
    assert db.execute.await_count == 3
    db.commit.assert_awaited_once()

    upsert_sql = str(
        db.execute.await_args_list[1].args[0].compile(dialect=mysql.dialect())
    )
    resolve_sql = str(
        db.execute.await_args_list[2].args[0].compile(dialect=mysql.dialect())
    )
    assert "ON DUPLICATE KEY UPDATE" in upsert_sql
    assert "UPDATE ods_wb_order_reshipment_orders" in resolve_sql


@pytest.mark.asyncio
async def test_empty_successful_snapshot_resolves_all_active_rows():
    moscow = ZoneInfo("Europe/Moscow")
    observed_at = datetime(2026, 7, 24, 3, 0, tzinfo=moscow)
    existing_result = Mock()
    existing_result.all.return_value = [
        SimpleNamespace(
            id=1,
            order_id=100,
            supply_id="WB-GI-1",
            is_active=True,
            first_seen_at=observed_at,
            status_changed_at=observed_at,
        )
    ]
    db = AsyncMock()
    db.execute.side_effect = [existing_result, Mock()]

    result = await CRUDODSWBReshipmentOrder().reconcile_snapshot(
        db,
        orders_data=[],
        shop_id=7,
        observed_at=observed_at,
    )

    assert result["count"] == 0
    assert result["resolved_count"] == 1
    assert db.execute.await_count == 2
    db.commit.assert_awaited_once()
