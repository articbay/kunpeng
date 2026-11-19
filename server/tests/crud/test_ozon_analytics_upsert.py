from datetime import date
from decimal import Decimal

import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.ozon.analytics import (
    crud_ods_ozon_analytics_data_daily,
    crud_ods_ozon_analytics_totals_window,
)
from kunpeng.models.base import Base
from kunpeng.models.ods.ozon.analytics import (
    ODSOzonAnalyticsDataDaily,
    ODSOzonAnalyticsTotalsWindow,
)


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                ODSOzonAnalyticsDataDaily.__table__,
                ODSOzonAnalyticsTotalsWindow.__table__,
            ],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as value:
        yield value
    await engine.dispose()


def _daily_item(revenue: str) -> dict:
    return {
        "sku": 1938260971,
        "sku_name": "Product",
        "stat_date": date(2026, 8, 23),
        "metrics": {"revenue": revenue, "ordered_units": 6},
        "requested_metrics_core": ["revenue", "ordered_units"],
        "requested_metrics_outcome": ["returns"],
        "row_data_core": {"metrics": [revenue, 6]},
        "row_data_outcome": {"metrics": [0]},
        "has_core_metrics": True,
        "has_outcome_metrics": True,
    }


async def test_analytics_daily_and_totals_are_idempotent(session: AsyncSession):
    window_start = date(2026, 8, 17)
    window_end = date(2026, 8, 23)
    await crud_ods_ozon_analytics_data_daily.upsert_many(
        session,
        shop_id=7,
        date_from=window_start,
        date_to=window_end,
        items=[_daily_item("10.50")],
    )
    await crud_ods_ozon_analytics_data_daily.upsert_many(
        session,
        shop_id=7,
        date_from=window_start,
        date_to=window_end,
        items=[_daily_item("20.75")],
    )
    await crud_ods_ozon_analytics_totals_window.upsert(
        session,
        shop_id=7,
        date_from=window_start,
        date_to=window_end,
        item={
            "metrics": {"revenue": "20.75"},
            "requested_metrics_core": ["revenue"],
            "requested_metrics_outcome": ["returns"],
            "raw_totals_core": [20.75],
            "raw_totals_outcome": [0],
        },
    )
    await session.commit()

    rows = (await session.execute(select(ODSOzonAnalyticsDataDaily))).scalars().all()
    totals = (
        (await session.execute(select(ODSOzonAnalyticsTotalsWindow))).scalars().all()
    )
    assert len(rows) == 1
    assert rows[0].revenue == Decimal("20.7500")
    assert len(totals) == 1
    assert totals[0].revenue == Decimal("20.7500")
