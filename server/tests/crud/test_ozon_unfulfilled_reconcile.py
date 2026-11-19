from datetime import datetime

import pytest
from sqlalchemy import BigInteger, create_engine, select, update
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from kunpeng.crud.ods.ozon.unfulfilled_postings import CRUDOzonUnfulfilledPosting
from kunpeng.models.ods.ozon.unfulfilled_postings import ODSOzonUnfulfilledPosting


@compiles(BigInteger, "sqlite")
def _compile_big_integer_as_integer(_type, compiler, **kwargs):
    return "INTEGER"


class AsyncSessionAdapter:
    def __init__(self, session: Session):
        self.session = session

    def get_bind(self):
        return self.session.get_bind()

    async def execute(self, statement):
        return self.session.execute(statement)

    async def commit(self):
        self.session.commit()


def _posting(status: str = "awaiting_packaging"):
    return {
        "posting_number": "P-1",
        "order_id": 101,
        "status": status,
        "cutoff_at": "2026-07-26T05:00:00Z",
        "delivering_date": "2026-07-27T05:00:00Z",
        "shipment_date_without_delay": "2026-07-26T04:00:00Z",
        "tracking_number": "TRACK-1",
        "available_actions": ["ship"],
        "requirements": {"products_requiring_gtd": []},
        "sorting_center": {"id": 77, "name": "SC"},
        "integration_type_flow": "ozon",
        "parent_posting_number": "PARENT-1",
        "destination_place_id": 88,
        "destination_place_name": "Moscow",
        "is_express": True,
        "is_multibox": True,
        "multi_box_qty": 2,
        "products": [{"sku": 55}],
    }


@pytest.mark.asyncio
async def test_atomic_upsert_preserves_first_seen_and_reconciles_state():
    engine = create_engine("sqlite://")
    ODSOzonUnfulfilledPosting.__table__.create(engine)
    first_observed = datetime(2026, 7, 26, 8, 0)
    second_observed = datetime(2026, 7, 26, 9, 0)
    sentinel_first_seen = datetime(2026, 7, 1, 12, 0)
    crud = CRUDOzonUnfulfilledPosting()

    with Session(engine) as session:
        db = AsyncSessionAdapter(session)
        first = await crud.reconcile_snapshot(
            db,
            items=[_posting()],
            shop_id=7,
            observed_at=first_observed,
        )
        await db.commit()
        session.execute(
            update(ODSOzonUnfulfilledPosting).values(first_seen_at=sentinel_first_seen)
        )
        session.commit()

        second = await crud.reconcile_snapshot(
            db,
            items=[_posting(status="awaiting_deliver")],
            shop_id=7,
            observed_at=second_observed,
        )
        await db.commit()
        rows = session.scalars(select(ODSOzonUnfulfilledPosting)).all()

        assert first["new_count"] == 1
        assert second["new_count"] == 0
        assert len(rows) == 1
        assert rows[0].status == "awaiting_deliver"
        assert rows[0].tracking_number == "TRACK-1"
        assert rows[0].available_actions == ["ship"]
        assert rows[0].requirements == {"products_requiring_gtd": []}
        assert rows[0].sorting_center == {"id": 77, "name": "SC"}
        assert rows[0].integration_type_flow == "ozon"
        assert rows[0].parent_posting_number == "PARENT-1"
        assert rows[0].destination_place_id == 88
        assert rows[0].destination_place_name == "Moscow"
        assert rows[0].is_express is True
        assert rows[0].is_multibox is True
        assert rows[0].multi_box_qty == 2
        assert rows[0].first_seen_at == sentinel_first_seen
        assert rows[0].last_seen_at == second_observed
        assert rows[0].is_active is True
        assert rows[0].resolved_at is None

        resolved = await crud.reconcile_snapshot(
            db,
            items=[],
            shop_id=7,
            observed_at=datetime(2026, 7, 26, 10, 0),
        )
        await db.commit()
        row = session.scalar(select(ODSOzonUnfulfilledPosting))
        assert resolved["resolved_count"] == 1
        assert row.is_active is False
        assert row.resolved_at == datetime(2026, 7, 26, 10, 0)

        reactivated = await crud.reconcile_snapshot(
            db,
            items=[_posting()],
            shop_id=7,
            observed_at=datetime(2026, 7, 26, 11, 0),
        )
        await db.commit()
        row = session.scalar(select(ODSOzonUnfulfilledPosting))
        assert reactivated["reactivated_count"] == 1
        assert row.is_active is True
        assert row.resolved_at is None
        assert row.first_seen_at == sentinel_first_seen


@pytest.mark.asyncio
async def test_active_row_without_returned_cutoff_is_resolved_when_missing():
    engine = create_engine("sqlite://")
    ODSOzonUnfulfilledPosting.__table__.create(engine)
    observed_at = datetime(2026, 7, 28, 1, 47)
    crud = CRUDOzonUnfulfilledPosting()

    with Session(engine) as session:
        session.add(
            ODSOzonUnfulfilledPosting(
                shop_id=7,
                row_data={"posting_number": "P-OLD"},
                posting_number="P-OLD",
                cutoff_at=None,
                last_seen_at=datetime(2026, 7, 27, 1, 0),
                is_active=True,
            )
        )
        session.commit()
        db = AsyncSessionAdapter(session)

        result = await crud.reconcile_snapshot(
            db,
            items=[],
            shop_id=7,
            observed_at=observed_at,
        )
        await db.commit()

        row = session.scalar(select(ODSOzonUnfulfilledPosting))
        assert result["resolved_count"] == 1
        assert row.is_active is False
        assert row.resolved_at == observed_at


def test_model_has_shop_posting_unique_constraint():
    assert (
        ODSOzonUnfulfilledPosting.__tablename__ == "ods_ozon_order_unfulfilled_postings"
    )
    names = {
        constraint.name
        for constraint in ODSOzonUnfulfilledPosting.__table__.constraints
        if constraint.name
    }
    assert "uq_ods_ozon_unfulfilled_postings_shop_posting" in names
