from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwm.ozon.order_lifecycle_detail import CRUDDWMOzonOrderLifecycleDetail
from kunpeng.models.dwm import DWMOzonOrderLifecycleDetail


def test_lifecycle_model_uses_order_product_posting_grain():
    assert [
        column.name for column in DWMOzonOrderLifecycleDetail.__table__.primary_key
    ] == ["shop_id", "fulfillment_type", "posting_number", "sku"]

    columns = DWMOzonOrderLifecycleDetail.__table__.columns
    assert columns.quantity.type.python_type is int
    assert columns.return_cnt.nullable is False
    assert columns.return_qty.nullable is False
    assert columns.in_process_at.comment.endswith("近似作为下单时间")
    assert "delivered_at" not in columns
    assert "review_id" not in columns
    assert "rating" not in columns


def test_refresh_sql_matches_return_source_at_safe_grain():
    sql = CRUDDWMOzonOrderLifecycleDetail._refresh_statement.text.upper()

    assert "FROM DWD_OZON_ORDER_DETAIL AS ORD" in sql
    assert "ODS_OZON_POSTING_STATUS_HISTORY" not in sql
    assert "DELIVERED_AT" not in sql
    assert "FROM DWD_OZON_RETURN_DETAIL" in sql
    assert "COUNT(DISTINCT RETURN_ID)" in sql
    assert "SUM(COALESCE(QUANTITY, 0))" in sql
    assert "MIN(RETURN_DATE)" in sql
    assert "ROW_NUMBER() OVER" in sql
    assert "UPPER(`SCHEMA`) AS FULFILLMENT_TYPE" in sql
    assert "RET.POSTING_NUMBER = ORD.POSTING_NUMBER" in sql
    assert "RET.SKU = ORD.SKU" in sql
    assert "LATEST.POSTING_NUMBER = ORD.POSTING_NUMBER" in sql
    assert "LATEST.SKU = ORD.SKU" in sql
    assert "DWD_OZON_CUSTOMER_VOICE_DETAIL" not in sql
    assert "ON DUPLICATE KEY UPDATE" in sql


def test_cleanup_and_quality_sql_use_complete_business_keys():
    cleanup_sql = CRUDDWMOzonOrderLifecycleDetail._delete_stale_statement.text.upper()
    unmatched_sql = (
        CRUDDWMOzonOrderLifecycleDetail._unmatched_return_statement.text.upper()
    )

    for fragment in (
        "ORD.SHOP_ID = TARGET.SHOP_ID",
        "ORD.FULFILLMENT_TYPE = TARGET.FULFILLMENT_TYPE",
        "ORD.POSTING_NUMBER = TARGET.POSTING_NUMBER",
        "ORD.SKU = TARGET.SKU",
    ):
        assert fragment in cleanup_sql

    for fragment in (
        "ORD.SHOP_ID = RET.SHOP_ID",
        "ORD.FULFILLMENT_TYPE = UPPER(RET.`SCHEMA`)",
        "ORD.POSTING_NUMBER = RET.POSTING_NUMBER",
        "ORD.SKU = RET.NM_ID",
    ):
        assert fragment in unmatched_sql


@pytest.mark.asyncio
async def test_refresh_executes_upsert_cleanup_and_quality_count_without_commit():
    crud = CRUDDWMOzonOrderLifecycleDetail()
    db = AsyncMock()
    refresh_result = Mock(rowcount=5)
    stale_result = Mock(rowcount=1)
    unmatched_result = Mock()
    unmatched_result.scalar_one.return_value = 2
    db.execute.side_effect = [refresh_result, stale_result, unmatched_result]

    result = await crud.refresh_order_date_range(
        db,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
        shop_id=7,
    )

    assert result == {
        "affected_rows": 5,
        "deleted_stale_rows": 1,
        "unmatched_return_rows": 2,
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
    crud = CRUDDWMOzonOrderLifecycleDetail()
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
