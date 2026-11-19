from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.ozon.return_detail import CRUDDWDOzonReturnDetail
from kunpeng.crud.ods.ozon.returns import CRUDOzonReturn, CRUDOzonReturnStorage
from kunpeng.models.dwd.ozon import DWDOzonReturnDetail
from kunpeng.models.ods.ozon.returns import ODSOzonReturn, ODSOzonReturnStorage


def test_ozon_return_dwd_model_keeps_compatibility_identifiers():
    columns = list(DWDOzonReturnDetail.__table__.columns.keys())

    assert columns[:3] == ["shop_id", "return_id", "nm_id"]
    assert "srid" in columns
    assert DWDOzonReturnDetail.nm_id.comment == "Ozon SKU（沿用nm_id命名）"
    assert "order_number" in DWDOzonReturnDetail.srid.comment
    assert columns.index("category_name_cn") == columns.index("category_name") + 1
    assert columns.index("product_name_cn") == columns.index("product_name") + 1
    assert (
        columns.index("status_display_name_cn")
        == columns.index("status_display_name") + 1
    )
    assert (
        columns.index("compensation_status_display_name_cn")
        == columns.index("compensation_status_display_name") + 1
    )
    assert (
        columns.index("return_reason_name_cn")
        == columns.index("return_reason_name") + 1
    )
    assert columns.index("buyer_comment_cn") == columns.index("buyer_comment") + 1
    assert columns.index("place_name_cn") == columns.index("place_name") + 1
    assert columns.index("place_address_cn") == columns.index("place_address") + 1
    assert (
        columns.index("target_place_name_cn") == columns.index("target_place_name") + 1
    )
    assert (
        columns.index("target_place_address_cn")
        == columns.index("target_place_address") + 1
    )
    assert [column.name for column in DWDOzonReturnDetail.__table__.primary_key] == [
        "shop_id",
        "return_id",
        "nm_id",
    ]


def test_return_storage_extracts_v1_returns_list_storage_object():
    crud = CRUDOzonReturnStorage(ODSOzonReturnStorage)

    record = crud._extract_item_data(
        {
            "storage": {
                "days": 3,
                "arrived_moment": "2026-08-01T10:00:00Z",
                "tariffication_first_date": "2026-08-05T10:00:00Z",
                "tariffication_start_date": "2026-08-06T10:00:00Z",
                "utilization_forecast_date": "2026-09-01T10:00:00Z",
                "sum": {"price": "12.50", "currency_code": "RUB"},
                "utilization_sum": {"price": "30", "currency_code": "RUB"},
            }
        },
        shop_id=7,
        return_id=99,
    )

    assert record["shop_id"] == 7
    assert record["return_id"] == 99
    assert record["storage_days"] == 3
    assert record["storage_fee_currency"] == "RUB"
    assert record["arrived_moment"] is not None


def test_return_extracts_nested_compensation_status_and_optional_buyer_comment():
    crud = CRUDOzonReturn(ODSOzonReturn)

    record = crud._extract_item_data(
        {
            "id": 99,
            "compensation_status": {
                "status": {
                    "id": 2,
                    "display_name": "Компенсация получена",
                    "sys_name": "Received",
                },
                "change_moment": "2026-08-03T12:30:00Z",
            },
            "buyer_comment": "Не подошёл размер",
        },
        shop_id=7,
    )

    assert record["compensation_status"] == "Received"
    assert record["compensation_status_id"] == 2
    assert record["compensation_status_display_name"] == "Компенсация получена"
    assert record["compensation_status_sys_name"] == "Received"
    assert record["compensation_status_change_moment"] is not None
    assert record["buyer_comment"] == "Не подошёл размер"


@pytest.mark.asyncio
async def test_ozon_return_dwd_upsert_maps_nm_id_and_srid():
    crud = CRUDDWDOzonReturnDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 4
    upsert_result = Mock()
    upsert_result.rowcount = 4
    db.execute.side_effect = [count_result, upsert_result]

    result = await crud.upsert_from_ods(db, shop_id=7)

    assert result == {"source_count": 4, "affected_rows": 4}
    statement = str(db.execute.await_args_list[1].args[0])
    assert "p.sku AS source_nm_id" in statement
    assert "r.order_number AS source_srid" in statement
    assert "storage.arrived_moment AS source_ready_to_pickup_at" in statement
    assert "r.`schema` AS source_schema" in statement
    assert "fbs.in_process_at" in statement
    assert "r.compensation_status_display_name" in statement
    assert "r.compensation_status_change_moment" in statement
    assert "r.buyer_comment AS source_buyer_comment" in statement
    assert "storage.storage_fee_amount AS source_storage_fee_amount" in statement
    assert "p.commission_percent AS source_commission_percent" in statement
    assert "p.price_without_commission_amount" in statement
    assert "catalog.category_name AS source_category_name" in statement
    assert "MAX(category_name) AS category_name" in statement
    assert "ON DUPLICATE KEY UPDATE" in statement
    assert "product_name_cn = IF(" in statement
    assert "target_place_address_cn = IF(" in statement
    assert "compensation_status_display_name_cn = IF(" in statement
    assert "buyer_comment_cn = IF(" in statement
    assert "VALUES(" not in statement
    assert db.execute.await_args_list[1].args[1] == {"shop_id": 7}
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_ozon_return_dwd_does_not_write_without_products():
    crud = CRUDDWDOzonReturnDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.flush.assert_not_awaited()
