"""Ozon 广告 SKU 日统计 CRUD 批内幂等（去重）单元测试

复现并回归 1062 唯一键冲突：同一次报表 rows 中出现重复的
(sku, stat_date)，若仅按 DB 查询判断存在性，pending(未 flush) 的新对象
查询不到，会导致同批两条都走新增分支，flush 时触发
`uq_ods_ozon_adv_stats_product_daily_key` 唯一约束冲突。

这里用内存 SQLite 建表后，验证 create_many 能在批内去重、后值覆盖前值，
且不会抛 IntegrityError。
"""

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.ozon.adverts import crud_ods_ozon_adv_stat_product_daily
from kunpeng.models.base import Base
from kunpeng.models.ods.ozon.adverts import ODSOzonAdvStatProductDaily


# 测试用：SQLite 下 BigInteger 主键无法作为 rowid 别名自增，渲染成 INTEGER
# 使自增主键在内存库可用（仅影响本测试的建表 DDL，不改动生产模型）。
@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[ODSOzonAdvStatProductDaily.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _row(sku: int, date_str: str, clicks: int) -> dict:
    return {"sku": sku, "date": date_str, "clicks": clicks, "title": f"sku-{sku}"}


async def test_create_many_dedups_within_batch(session: AsyncSession):
    """同批出现重复 (sku, date) 时不冲突，且后值覆盖前值"""
    rows = [
        _row(2098681011, "14.07.2026", 3),
        _row(2098681011, "14.07.2026", 9),  # 同键重复，应覆盖为 9
        _row(2222222222, "14.07.2026", 5),
    ]

    result = await crud_ods_ozon_adv_stat_product_daily.create_many(
        session, items=rows, shop_id=2, campaign_id="29020622"
    )
    await session.commit()

    # 结果集里去重后应为 2 条
    assert len(result) == 2

    persisted = (
        (await session.execute(select(ODSOzonAdvStatProductDaily))).scalars().all()
    )
    assert len(persisted) == 2

    dup = next(r for r in persisted if r.sku == 2098681011)
    assert dup.clicks == 9  # 后值覆盖前值


async def test_create_many_updates_existing_across_calls(session: AsyncSession):
    """跨批(已入库)相同键走更新分支，不新增"""
    await crud_ods_ozon_adv_stat_product_daily.create_many(
        session,
        items=[_row(2098681011, "14.07.2026", 3)],
        shop_id=2,
        campaign_id="29020622",
    )
    await session.commit()

    await crud_ods_ozon_adv_stat_product_daily.create_many(
        session,
        items=[_row(2098681011, "14.07.2026", 7)],
        shop_id=2,
        campaign_id="29020622",
    )
    await session.commit()

    persisted = (
        (await session.execute(select(ODSOzonAdvStatProductDaily))).scalars().all()
    )
    assert len(persisted) == 1
    assert persisted[0].clicks == 7
