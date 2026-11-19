"""Wildberries 卖家余额快照幂等写入测试。"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.wildberries.seller_balance import \
    crud_ods_wb_seller_balance
from kunpeng.models.base import Base
from kunpeng.models.ods.wildberries.seller_balance import ODSWBSellerBalance


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    """让 SQLite 测试中的 BigInteger 主键支持自增。"""
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[ODSWBSellerBalance.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_snapshot_updates_same_shop_and_date(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    snapshot_date = date(2026, 7, 23)
    synced_at = datetime(2026, 7, 23, 3, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    monkeypatch.setattr(
        "kunpeng.crud.ods.wildberries.seller_balance.today_platform",
        lambda: snapshot_date,
    )
    monkeypatch.setattr(
        "kunpeng.crud.ods.wildberries.seller_balance.now_platform",
        lambda: synced_at,
    )

    await crud_ods_wb_seller_balance.upsert_snapshot(
        session,
        shop_id=1,
        balance_data={
            "currency": "RUB",
            "current": 100.25,
            "for_withdraw": 80.00,
        },
    )
    await crud_ods_wb_seller_balance.upsert_snapshot(
        session,
        shop_id=1,
        balance_data={
            "currency": "RUB",
            "current": 150.50,
            "for_withdraw": 120.00,
        },
    )

    rows = (await session.execute(select(ODSWBSellerBalance))).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].current) == 150.50
    assert float(rows[0].for_withdraw) == 120.00
    assert rows[0].snapshot_date == snapshot_date
