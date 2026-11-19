"""Wildberries 搜索流量幂等写入测试。"""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.wildberries.search_traffic import crud_ods_wb_search_traffic
from kunpeng.models.base import Base
from kunpeng.models.ods.wildberries.search_traffic import ODSWBSearchTraffic


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[ODSWBSearchTraffic.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_updates_same_product_and_window(session: AsyncSession):
    window = {
        "shop_id": 1,
        "date_from": date(2026, 7, 17),
        "date_to": date(2026, 7, 23),
        "currency": "RUB",
        "position_cluster": "all",
    }
    first = {
        "nmId": 101,
        "name": "Перчатки",
        "avgPosition": {"current": 25, "dynamics": 2},
        "openCard": {"current": 10, "dynamics": 1},
    }
    updated = {
        **first,
        "avgPosition": {"current": 20, "dynamics": 5},
        "openCard": {"current": 30, "dynamics": 3},
    }

    await crud_ods_wb_search_traffic.upsert_many(
        session,
        products=[first],
        **window,
    )
    await crud_ods_wb_search_traffic.upsert_many(
        session,
        products=[updated],
        **window,
    )

    rows = (await session.execute(select(ODSWBSearchTraffic))).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].avg_position_current) == 20
    assert rows[0].open_card_current == 30
