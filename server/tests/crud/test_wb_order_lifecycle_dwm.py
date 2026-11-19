from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwm.wildberries.order_lifecycle_detail import (
    CRUDDWMWBOrderLifecycleDetail,
)
from kunpeng.models.dwm import DWMWBOrderLifecycleDetail


def test_lifecycle_model_uses_shop_and_srid_grain():
    assert [
        column.name for column in DWMWBOrderLifecycleDetail.__table__.primary_key
    ] == ["shop_id", "srid"]
    columns = DWMWBOrderLifecycleDetail.__table__.columns
    assert columns["order_at"].nullable is False
    for name in (
        "has_statistics_order_data",
        "has_marketplace_order_data",
        "has_supply_data",
        "has_sale_data",
        "has_finance_data",
        "has_return_data",
    ):
        assert columns[name].nullable is False


def test_refresh_sql_uses_union_spine_and_preaggregated_sources():
    sql = CRUDDWMWBOrderLifecycleDetail._refresh_statement.text.upper()
    assert "FROM DWD_WB_ORDER_STATISTICS_DETAIL" in sql
    assert "FROM ODS_WB_MARKETPLACE_ORDERS" in sql
    assert "UNION ALL" in sql
    assert "PARTITION BY SOURCE.SHOP_ID, SOURCE.RID" in sql
    assert "GROUP BY SOURCE.SHOP_ID, SOURCE.SRID" in sql
    assert "GROUP BY SHOP_ID, SRID" in sql


def test_return_links_require_unique_business_identity_and_never_guess_by_sku_date():
    sql = CRUDDWMWBOrderLifecycleDetail._refresh_statement.text.upper()
    assert "COUNT(DISTINCT SRID) AS SRID_COUNT" in sql
    assert "FINANCE_SRID_COUNT = 1" in sql
    assert "HAS_IDENTITY_CONFLICT = 1 THEN NULL" in sql
    assert "MARKETPLACE_BY_ORDER.ORDER_ID = RETURNS.ORDER_ID" in sql
    assert "BRIDGE.ORDER_ID = RETURNS.ORDER_ID" in sql
    assert "RETURNS.NM_ID =" not in sql
    assert "RETURNS.ORDER_DT =" not in sql


def test_stage_rules_do_not_treat_complete_or_sorted_as_sold():
    sql = CRUDDWMWBOrderLifecycleDetail._refresh_statement.text.upper()
    assert "SOURCE.WB_STATUS = 'SOLD'" in sql
    assert "SOURCE.WB_STATUS = 'SORTED' THEN 'WB_RECEIVED'" in sql
    assert "SOURCE.SUPPLIER_STATUS IN ('COMPLETE', 'DELIVER')" in sql
    assert "THEN 'IN_DELIVERY'" in sql
    assert "SOURCE.FINANCE_SALE_ROW_CNT > 0" in sql


def test_refresh_uses_canonical_lifecycle_status_dictionary_before_stored_text():
    sql = CRUDDWMWBOrderLifecycleDetail._refresh_statement.text.upper()
    assert "CASE LOWER(TRIM(SOURCE.WB_STATUS))" in sql
    assert "WHEN 'SORTED' THEN 'WB已接收并分拣'" in sql
    assert "ELSE SOURCE.WB_STATUS_CN" in sql
    assert "CASE LOWER(TRIM(SOURCE.SUPPLIER_STATUS))" in sql
    assert "WHEN 'CONFIRM' THEN '组装中'" in sql
    assert "ELSE SOURCE.SUPPLIER_STATUS_CN" in sql
    assert "COALESCE(SOURCE.WB_STATUS_CN" not in sql


def test_cleanup_uses_both_order_spine_sources():
    sql = CRUDDWMWBOrderLifecycleDetail._delete_stale_statement.text.upper()
    assert sql.count("NOT EXISTS") == 2
    assert "STATS.SRID = TARGET.SRID" in sql
    assert "MARKETPLACE.RID = TARGET.SRID" in sql


@pytest.mark.asyncio
async def test_refresh_returns_data_quality_counts_without_committing():
    crud = CRUDDWMWBOrderLifecycleDetail()
    db = AsyncMock()
    refresh_result = Mock(rowcount=9)
    cleanup_result = Mock(rowcount=1)
    quality_result = Mock()
    quality_result.mappings.return_value.one.return_value = {
        "unmatched_return_rows": 2,
        "ambiguous_return_rows": 0,
    }
    missing_srid_result = Mock()
    missing_srid_result.scalar_one.return_value = 3
    db.execute.side_effect = [
        refresh_result,
        cleanup_result,
        quality_result,
        missing_srid_result,
    ]

    result = await crud.refresh_order_date_range(
        db,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        shop_id=8,
    )

    assert result == {
        "affected_rows": 9,
        "deleted_stale_rows": 1,
        "unmatched_return_rows": 2,
        "ambiguous_return_rows": 0,
        "marketplace_missing_srid_rows": 3,
    }
    assert db.execute.await_count == 4
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_scope():
    crud = CRUDDWMWBOrderLifecycleDetail()
    db = AsyncMock()
    with pytest.raises(ValueError, match="date_from"):
        await crud.refresh_order_date_range(
            db,
            date_from=date(2026, 8, 2),
            date_to=date(2026, 8, 1),
        )
    with pytest.raises(ValueError, match="shop_id"):
        await crud.refresh_order_date_range(
            db,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 2),
            shop_id=0,
        )
    db.execute.assert_not_awaited()
