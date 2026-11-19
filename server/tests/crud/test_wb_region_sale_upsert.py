"""Wildberries 区域销售报告幂等写入测试。"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.ext.compiler import compiles

from kunpeng.crud.ods.wildberries.region_sale import crud_ods_wb_region_sale
from kunpeng.models.base import Base
from kunpeng.models.ods.wildberries.region_sale import ODSWBRegionSale


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
            tables=[ODSWBRegionSale.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_many_updates_same_window_and_dimension(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "kunpeng.crud.ods.wildberries.region_sale.now_platform",
        lambda: datetime(2026, 7, 24, 3, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    window = {
        "shop_id": 1,
        "date_from": date(2026, 7, 22),
        "date_to": date(2026, 7, 23),
    }
    first = {
        "cityName": "Москва",
        "countryName": "Россия",
        "foName": "Центральный федеральный округ",
        "nmID": 177974431,
        "regionName": "Москва",
        "sa": "article-1",
        "saleInvoiceCostPrice": 100.00,
        "saleInvoiceCostPricePerc": 25.0,
        "saleItemInvoiceQty": 1,
    }
    updated = {
        **first,
        "saleInvoiceCostPrice": 250.00,
        "saleInvoiceCostPricePerc": 40.0,
        "saleItemInvoiceQty": 3,
    }

    await crud_ods_wb_region_sale.upsert_many(
        session,
        report_data=[first],
        **window,
    )
    await crud_ods_wb_region_sale.upsert_many(
        session,
        report_data=[updated],
        **window,
    )

    rows = (await session.execute(select(ODSWBRegionSale))).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].sale_invoice_cost_price) == 250.00
    assert rows[0].sale_item_invoice_qty == 3
