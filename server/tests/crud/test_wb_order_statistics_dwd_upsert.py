from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.order_statistics_detail import (
    CRUDDWDWBOrderStatisticsDetail,
)
from kunpeng.models.dwd.wildberries import DWDWBOrderStatisticsDetail


def test_wb_order_statistics_dwd_has_confirmed_columns_and_grain():
    assert list(DWDWBOrderStatisticsDetail.__table__.columns.keys()) == [
        "shop_id",
        "srid",
        "order_date",
        "last_change_date",
        "warehouse_name",
        "warehouse_name_cn",
        "country_name",
        "country_name_cn",
        "oblast_okrug_name",
        "oblast_okrug_name_cn",
        "region_name",
        "region_name_cn",
        "supplier_article",
        "nm_id",
        "barcode_ori",
        "barcode_hand",
        "category",
        "category_cn",
        "subject_name",
        "subject_name_cn",
        "tech_size",
        "tech_size_cn",
        "total_price",
        "discount_percent",
        "price_with_disc",
        "finished_price",
        "is_cancel",
        "cancel_date",
        "sticker_id",
        "g_number",
    ]
    primary_key = [
        column.name
        for column in DWDWBOrderStatisticsDetail.__table__.primary_key.columns
    ]
    assert primary_key == ["shop_id", "srid"]


@pytest.mark.asyncio
async def test_upsert_from_supplier_orders_maps_business_fields():
    crud = CRUDDWDWBOrderStatisticsDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 4
    upsert_result = Mock()
    upsert_result.rowcount = 5
    db.execute.side_effect = [count_result, upsert_result]

    result = await crud.upsert_from_ods(db, shop_id=8)

    assert result == {"source_count": 4, "affected_rows": 5}
    db.commit.assert_awaited_once()
    upsert_call = db.execute.await_args_list[1]
    normalized = " ".join(str(upsert_call.args[0]).lower().split())
    assert "from ods_wb_supplier_orders as stats_order" in normalized
    assert "stats_order.subject as source_subject_name" in normalized
    assert "trim(stats_order.barcode) regexp '^[0-9]{13}$'" in normalized
    assert "trim(stats_order.barcode) regexp '^[a-za-z0-9_-]+$'" in normalized
    assert "stats_order.sticker as source_sticker_id" in normalized
    assert "on duplicate key update" in normalized
    assert "values(" not in normalized
    assert upsert_call.args[1] == {"shop_id": 8}


@pytest.mark.asyncio
async def test_upsert_from_empty_supplier_orders_does_not_write():
    crud = CRUDDWDWBOrderStatisticsDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.commit.assert_not_awaited()
