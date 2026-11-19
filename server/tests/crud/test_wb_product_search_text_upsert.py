"""Wildberries 商品搜索词报告幂等写入测试。"""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.wildberries.product_search_text import (
    crud_ods_wb_product_search_text,
)
from kunpeng.models.base import Base
from kunpeng.models.ods.wildberries.product_search_text import ODSWBProductSearchText


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[ODSWBProductSearchText.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_updates_same_product_window_and_normalized_term(
    session: AsyncSession,
):
    window = {
        "shop_id": 1,
        "date_from": date(2026, 7, 22),
        "date_to": date(2026, 7, 23),
        "currency": "RUB",
        "top_order_by": "openCard",
    }
    first = {
        "text": " перчатки ",
        "nmId": 101,
        "name": "Перчатки",
        "openCard": {"current": 10, "dynamics": 1, "percentile": 50},
    }
    updated = {
        **first,
        "text": "перчатки",
        "openCard": {"current": 25, "dynamics": 2, "percentile": 60},
    }

    await crud_ods_wb_product_search_text.upsert_many(
        session,
        items=[first],
        **window,
    )
    await crud_ods_wb_product_search_text.upsert_many(
        session,
        items=[updated],
        **window,
    )

    rows = (await session.execute(select(ODSWBProductSearchText))).scalars().all()
    assert len(rows) == 1
    assert rows[0].search_text == "перчатки"
    assert rows[0].open_card_current == 25
