from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwm.wildberries.goods_oper_day import CRUDDWMWBGoodsOperDay
from kunpeng.models.dwm import DWMWBGoodsOperDay


def test_wb_goods_oper_day_uses_product_day_primary_key_and_source_flags():
    assert [column.name for column in DWMWBGoodsOperDay.__table__.primary_key] == [
        "stat_date",
        "shop_id",
        "nm_id",
    ]
    columns = DWMWBGoodsOperDay.__table__.columns
    for name in ("has_funnel_data", "has_order_data", "has_return_data", "has_ad_data"):
        assert columns[name].nullable is False
    for name in ("traffic_clicks", "ad_views", "ad_spend_amount", "ad_currency"):
        assert columns[name].nullable is True


def test_refresh_sql_uses_all_source_keys_and_daily_funnel_only():
    sql = CRUDDWMWBGoodsOperDay._refresh_statement.text.upper()
    assert "FROM DWD_WB_SALES_FUNNEL_DETAIL" in sql
    assert "FROM DWD_WB_ORDER_STATISTICS_DETAIL" in sql
    assert "FROM DWD_WB_RETURN_DETAIL" in sql
    assert "FROM DWD_WB_ADVERT_STATS_DAILY_INCR" in sql
    assert "DATE_FROM = DATE_TO" in sql
    assert sql.count(" UNION\n") >= 3


def test_refresh_sql_reaggregates_ratios_and_protects_currency():
    sql = CRUDDWMWBGoodsOperDay._refresh_statement.text.upper()
    assert "COUNT(DISTINCT CURRENCY) = 1" in sql
    assert "ADVERT.AD_CLICKS / ADVERT.AD_VIEWS" in sql
    assert "ADVERT.AD_ATTRIBUTED_SALES_AMOUNT / ADVERT.AD_SPEND_AMOUNT" in sql
    assert "AVG(CTR)" not in sql
    assert "AVG(CPC)" not in sql


def test_cleanup_keeps_any_source_only_product_day():
    sql = CRUDDWMWBGoodsOperDay._delete_stale_statement.text.upper()
    assert sql.count("NOT EXISTS") == 4
    assert "FUNNEL.DATE_TO = TARGET.STAT_DATE" in sql


@pytest.mark.asyncio
async def test_refresh_executes_upsert_cleanup_and_quality_checks():
    crud = CRUDDWMWBGoodsOperDay()
    db = AsyncMock()
    refresh_result = Mock(rowcount=7)
    cleanup_result = Mock(rowcount=2)
    quality_mapping = Mock()
    quality_mapping.mappings.return_value.one.return_value = {
        "order_rows": 3,
        "return_rows": 1,
    }
    db.execute.side_effect = [refresh_result, cleanup_result, quality_mapping]

    result = await crud.refresh_date_range(
        db,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        shop_id=8,
    )

    assert result == {
        "affected_rows": 7,
        "deleted_stale_rows": 2,
        "unattributed_order_rows": 3,
        "unattributed_return_rows": 1,
    }
    assert db.execute.await_count == 3
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_scope():
    crud = CRUDDWMWBGoodsOperDay()
    db = AsyncMock()
    with pytest.raises(ValueError, match="date_from"):
        await crud.refresh_date_range(
            db,
            date_from=date(2026, 8, 2),
            date_to=date(2026, 8, 1),
        )
    with pytest.raises(ValueError, match="shop_id"):
        await crud.refresh_date_range(
            db,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 2),
            shop_id=0,
        )
    db.execute.assert_not_awaited()
