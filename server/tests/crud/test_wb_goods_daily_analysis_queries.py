from datetime import date

from sqlalchemy import select

from kunpeng.crud.dwm.wildberries.goods_daily_analysis import (
    CRUDDWMWBGoodsDailyAnalysis,
)
from kunpeng.models.dwm import DWMWBGoodsOperDay


def test_wb_goods_query_applies_shop_permissions_and_filters():
    query = CRUDDWMWBGoodsDailyAnalysis()._apply_filters(
        select(DWMWBGoodsOperDay),
        allowed_shop_ids=[1, 4],
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
        nm_id=123,
        data_status="has_funnel",
    )
    sql = str(query).upper()

    assert "SHOP_ID IN" in sql
    assert "STAT_DATE >=" in sql
    assert "STAT_DATE <=" in sql
    assert "NM_ID =" in sql
    assert "HAS_FUNNEL_DATA IS TRUE" in sql


def test_wb_goods_query_supports_data_quality_anomalies():
    query = CRUDDWMWBGoodsDailyAnalysis()._apply_filters(
        select(DWMWBGoodsOperDay),
        allowed_shop_ids=[1],
        anomaly="click_scope_conflict",
    )

    assert "HAS_CLICK_SCOPE_CONFLICT IS TRUE" in str(query).upper()


def test_wb_goods_query_forces_empty_result_without_shop_permissions():
    query = CRUDDWMWBGoodsDailyAnalysis()._apply_filters(
        select(DWMWBGoodsOperDay), allowed_shop_ids=[]
    )

    assert "false" in str(query).lower()
