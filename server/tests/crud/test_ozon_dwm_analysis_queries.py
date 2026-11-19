from datetime import date

from sqlalchemy import select

from kunpeng.crud.dwm.ozon.goods_daily_analysis import CRUDDWMOzonGoodsDailyAnalysis
from kunpeng.crud.dwm.ozon.order_lifecycle_query import CRUDDWMOzonOrderLifecycleQuery
from kunpeng.models.dwm import DWMOzonGoodsTradeReturnDay, DWMOzonOrderLifecycleDetail


def test_goods_query_always_applies_shop_permissions_and_anomaly():
    crud = CRUDDWMOzonGoodsDailyAnalysis()
    query = crud._apply_filters(
        select(DWMOzonGoodsTradeReturnDay),
        allowed_shop_ids=[3, 7],
        anomaly="ad_spend_no_orders",
    )
    sql = str(query).upper()

    assert "SHOP_ID IN" in sql
    assert "AD_SPEND_AMOUNT" in sql
    assert "AD_ATTRIBUTED_ORDER_CNT" in sql


def test_lifecycle_query_uses_index_friendly_order_range_and_shop_permissions():
    crud = CRUDDWMOzonOrderLifecycleQuery()
    query = crud._apply_filters(
        select(DWMOzonOrderLifecycleDetail),
        allowed_shop_ids=[3],
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
        stage="returned",
    )
    sql = str(query).upper()

    assert "SHOP_ID IN" in sql
    assert "IN_PROCESS_AT >=" in sql
    assert "IN_PROCESS_AT <" in sql
    assert "RETURN_CNT >" in sql
    assert "DATE(" not in sql


def test_empty_shop_permissions_force_empty_result():
    goods_query = CRUDDWMOzonGoodsDailyAnalysis()._apply_filters(
        select(DWMOzonGoodsTradeReturnDay), allowed_shop_ids=[]
    )
    lifecycle_query = CRUDDWMOzonOrderLifecycleQuery()._apply_filters(
        select(DWMOzonOrderLifecycleDetail), allowed_shop_ids=[]
    )

    assert "false" in str(goods_query).lower()
    assert "false" in str(lifecycle_query).lower()
