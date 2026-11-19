from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.order_detail import CRUDDWDWBOrderDetail
from kunpeng.models.dwd.wildberries import DWDWBOrderDetail


def test_wb_order_dwd_model_has_confirmed_business_columns():
    assert list(DWDWBOrderDetail.__table__.columns.keys()) == [
        "shop_id",
        "order_id",
        "supply_id",
        "sticker_id",
        "order_dt",
        "title",
        "title_cn",
        "tech_size",
        "tech_size_cn",
        "color",
        "color_cn",
        "barcode_ori",
        "barcode_hand",
        "retail_price",
        "currency",
        "nm_id",
        "supplier_article",
        "warehouse_id",
        "warehouse_name",
        "warehouse_name_cn",
        "wb_status",
        "wb_status_cn",
        "address",
        "address_cn",
        "is_b2b",
        "delivery_type",
        "supplier_status",
        "supplier_status_cn",
        "is_cancellable",
        "price",
        "converted_price",
        "currency_code",
        "converted_currency_code",
        "office_id",
        "cargo_type",
        "cross_border_type",
        "is_zero_order",
    ]
    assert DWDWBOrderDetail.order_id.comment == "工作编号"
    assert DWDWBOrderDetail.nm_id.comment == "WB货号"


@pytest.mark.asyncio
async def test_upsert_from_ods_uses_the_confirmed_single_field_sources():
    crud = CRUDDWDWBOrderDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 2
    upsert_result = Mock()
    upsert_result.rowcount = 3
    db.execute.side_effect = [count_result, upsert_result]

    result = await crud.upsert_from_ods(db, shop_id=8)

    assert result == {"source_count": 2, "affected_rows": 3}
    db.commit.assert_awaited_once()
    upsert_call = db.execute.await_args_list[1]
    statement = str(upsert_call.args[0])
    normalized = " ".join(statement.lower().split())
    assert "on duplicate key update" in normalized
    assert "from ods_wb_marketplace_orders as marketplace" in normalized
    assert "report.sticker_id is not null" in normalized
    assert "report.retail_price is not null" in normalized
    assert "order by report.rr_date desc" in normalized
    assert "coalesce(marketplace.skus, json_array())" in normalized
    assert "json_table(" in normalized
    assert "regexp '^[0-9]{13}$'" in normalized
    assert "regexp '^[a-za-z0-9_-]+$'" in normalized
    assert "json_extract(marketplace.options, '$.isb2b')" in normalized
    assert "funnel.nm_id = marketplace.nm_id" in normalized
    assert "stats_order.srid = marketplace.rid" in normalized
    assert "select report.title" not in normalized
    assert "select report.tech_size" not in normalized
    assert "select report.sku" not in normalized
    assert "select stats_order.barcode" not in normalized
    assert "marketplace.delivery_type as source_delivery_type" in normalized
    assert "marketplace.supplier_status as source_supplier_status" in normalized
    assert "marketplace.is_cancellable as source_is_cancellable" in normalized
    assert (
        "marketplace.converted_currency_code as source_converted_currency_code"
        in normalized
    )
    assert "converted_currency_code = source_converted_currency_code" in normalized
    assert "values(" not in normalized
    assert upsert_call.args[1] == {"shop_id": 8}


@pytest.mark.asyncio
async def test_upsert_from_empty_marketplace_orders_does_not_write():
    crud = CRUDDWDWBOrderDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.commit.assert_not_awaited()
