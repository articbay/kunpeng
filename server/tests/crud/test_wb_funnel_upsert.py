"""Tests for idempotent Wildberries sales funnel persistence."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.wildberries.funnel import crud_ods_wb_sales_funnel
from kunpeng.models.base import Base
from kunpeng.models.ods.wildberries.funnel import ODSWBSalesFunnel


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    """Allow BigInteger primary keys to autoincrement in SQLite tests."""
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[ODSWBSalesFunnel.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


def _row(nm_id: int, order_count: int) -> dict:
    return {
        "product": {
            "nmId": nm_id,
            "vendorCode": f"vendor-{nm_id}",
        },
        "statistic": {"selected": {"orderCount": order_count}},
    }


@pytest.mark.asyncio
async def test_create_many_deduplicates_nested_nm_id_within_batch(
    session: AsyncSession,
):
    result = await crud_ods_wb_sales_funnel.create_many(
        session,
        funnel_data=[_row(12345, 2), _row(12345, 7), _row(67890, 3)],
        shop_id=1,
        date_from=date(2026, 7, 20),
        date_to=date(2026, 7, 20),
    )

    persisted = (
        (await session.execute(select(ODSWBSalesFunnel))).scalars().all()
    )
    assert len(result) == 2
    assert len(persisted) == 2
    assert next(row for row in persisted if row.nm_id == 12345).order_count == 7


@pytest.mark.asyncio
async def test_create_many_updates_existing_nested_nm_id(session: AsyncSession):
    kwargs = {
        "shop_id": 1,
        "date_from": date(2026, 7, 20),
        "date_to": date(2026, 7, 20),
    }
    await crud_ods_wb_sales_funnel.create_many(
        session, funnel_data=[_row(12345, 2)], **kwargs
    )
    await crud_ods_wb_sales_funnel.create_many(
        session, funnel_data=[_row(12345, 9)], **kwargs
    )

    persisted = (
        (await session.execute(select(ODSWBSalesFunnel))).scalars().all()
    )
    assert len(persisted) == 1
    assert persisted[0].order_count == 9


@pytest.mark.asyncio
async def test_create_many_rolls_back_failed_commit():
    db = Mock()
    db.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))
    db.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()

    with pytest.raises(RuntimeError, match="commit failed"):
        await crud_ods_wb_sales_funnel.create_many(
            db,
            funnel_data=[_row(12345, 2)],
            shop_id=1,
            date_from=date(2026, 7, 20),
            date_to=date(2026, 7, 20),
        )

    db.rollback.assert_awaited_once()
