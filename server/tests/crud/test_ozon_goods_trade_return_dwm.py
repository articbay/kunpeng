from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

# isort: off
from kunpeng.crud.dwm.ozon.goods_trade_return_day import (
    CRUDDWMOzonGoodsTradeReturnDay,
)

# isort: on
from kunpeng.models.dwm import DWMOzonGoodsTradeReturnDay


def test_dwm_model_uses_order_date_shop_sku_grain_and_safe_amounts():
    assert [
        column.name for column in DWMOzonGoodsTradeReturnDay.__table__.primary_key
    ] == ["stat_date", "shop_id", "sku"]

    columns = DWMOzonGoodsTradeReturnDay.__table__.columns
    assert columns.sku.type.python_type is int
    assert columns.sales_amount_sum.nullable is True
    assert columns.return_amount_sum.nullable is True
    assert columns.return_rate_ordered.comment.endswith("（0-1）")
    assert columns.return_rate_delivered.comment.endswith("（0-1）")
    assert columns.has_currency_conflict.nullable is False
    assert columns.has_funnel_data.nullable is False
    assert columns.has_traffic_metrics.nullable is False
    assert columns.has_ad_data.nullable is False
    for name in (
        "funnel_ordered_units",
        "funnel_revenue",
        "traffic_views",
        "traffic_visitors",
        "traffic_to_cart",
        "traffic_cart_rate",
        "ad_views",
        "ad_clicks",
        "ad_to_cart",
        "ad_spend_amount",
    ):
        assert columns[name].nullable is True


def test_refresh_sql_preaggregates_sources_and_emulates_full_outer_join():
    sql = CRUDDWMOzonGoodsTradeReturnDay._refresh_statement.text.upper()

    assert "FULL JOIN" not in sql
    assert "UNION" in sql
    assert "COUNT(DISTINCT FULFILLMENT_TYPE, POSTING_NUMBER)" in sql
    assert "GROUP BY IN_PROCESS_DATE, SHOP_ID, SKU" in sql
    assert "GROUP BY DATE(ORDER_DATE), SHOP_ID, NM_ID" in sql
    assert "FROM DWD_OZON_SALES_FUNNEL_DETAIL" in sql
    assert "FROM DWD_OZON_ADVERT_EFFICIENCY_DETAIL" in sql
    assert "COUNT(HITS_VIEW) = 0 THEN NULL" in sql
    assert "COUNT(ORDERED_UNITS) = 0 THEN NULL" in sql
    assert "COUNT(REVENUE) = 0 THEN NULL" in sql
    assert "COUNT(MONEY_SPENT) = 0 THEN NULL" in sql
    assert "COUNT(DISTINCT CAMPAIGN_ID)" in sql
    assert "AVG(" not in sql
    assert "ON DUPLICATE KEY UPDATE" in sql


def test_refresh_sql_recomputes_rates_and_keeps_source_only_keys():
    sql = CRUDDWMOzonGoodsTradeReturnDay._refresh_statement.text.upper()

    assert "ADVERT.AD_CLICKS / ADVERT.AD_VIEWS" in sql
    assert "ADVERT.AD_TO_CART / ADVERT.AD_CLICKS" in sql
    assert "FUNNEL.TRAFFIC_TO_CART / FUNNEL.TRAFFIC_VISITORS" in sql
    assert "SELECT STAT_DATE, SHOP_ID, SKU" in sql

    cleanup_sql = CRUDDWMOzonGoodsTradeReturnDay._delete_stale_statement.text.upper()
    assert "DWD_OZON_SALES_FUNNEL_DETAIL" in cleanup_sql
    assert "DWD_OZON_ADVERT_EFFICIENCY_DETAIL" in cleanup_sql


def test_every_funnel_source_key_is_kept_even_when_visible_metrics_are_zero():
    sql = CRUDDWMOzonGoodsTradeReturnDay._refresh_statement.text.upper()
    cleanup_sql = CRUDDWMOzonGoodsTradeReturnDay._delete_stale_statement.text.upper()

    assert "FROM DWD_OZON_SALES_FUNNEL_DETAIL" in sql
    assert "COALESCE(ORDERED_UNITS, 0) > 0" not in sql
    assert "COALESCE(FUNNEL.ORDERED_UNITS, 0) > 0" not in cleanup_sql
    assert "FUNNEL_ORDERED_UNITS = VALUES(FUNNEL_ORDERED_UNITS)" in sql
    assert "FUNNEL_REVENUE = VALUES(FUNNEL_REVENUE)" in sql


def test_refresh_sql_guards_mixed_or_missing_currencies():
    sql = CRUDDWMOzonGoodsTradeReturnDay._refresh_statement.text.upper()

    assert "COUNT(DISTINCT NULLIF(PRODUCT_CURRENCY, ''))" in sql
    assert "COUNT(DISTINCT NULLIF(PRICE_CURRENCY, ''))" in sql
    assert "COUNT(DISTINCT NULLIF(STORAGE_FEE_CURRENCY, ''))" in sql
    assert "COUNT(DISTINCT NULLIF(UTILIZATION_FEE_CURRENCY, ''))" in sql
    assert "COUNT(DISTINCT NULLIF(COMMISSION_CURRENCY, ''))" in sql
    assert "HAS_CURRENCY_CONFLICT" in sql


@pytest.mark.asyncio
async def test_refresh_executes_upsert_cleanup_and_quality_count_without_commit():
    crud = CRUDDWMOzonGoodsTradeReturnDay()
    db = AsyncMock()
    refresh_result = Mock(rowcount=4)
    stale_result = Mock(rowcount=1)
    unattributed_result = Mock()
    unattributed_result.scalar_one.return_value = 2
    db.execute.side_effect = [refresh_result, stale_result, unattributed_result]

    result = await crud.refresh_order_date_range(
        db,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
        shop_id=7,
    )

    assert result == {
        "affected_rows": 4,
        "deleted_stale_rows": 1,
        "unattributed_return_rows": 2,
    }
    assert db.execute.await_count == 3
    assert db.execute.await_args_list[0].args[1] == {
        "date_from": date(2026, 8, 1),
        "date_to": date(2026, 8, 31),
        "shop_id": 7,
    }
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_scope_before_database_access():
    crud = CRUDDWMOzonGoodsTradeReturnDay()
    db = AsyncMock()

    with pytest.raises(ValueError, match="date_from"):
        await crud.refresh_order_date_range(
            db,
            date_from=date(2026, 9, 1),
            date_to=date(2026, 8, 31),
        )
    with pytest.raises(ValueError, match="shop_id"):
        await crud.refresh_order_date_range(
            db,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 31),
            shop_id=0,
        )

    db.execute.assert_not_awaited()
