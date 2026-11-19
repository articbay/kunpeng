from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.return_detail import CRUDDWDWBReturnDetail
from kunpeng.models.dwd.wildberries import DWDWBReturnDetail


def test_wb_return_dwd_model_has_only_confirmed_business_columns():
    assert list(DWDWBReturnDetail.__table__.columns.keys()) == [
        "shop_id",
        "brand",
        "subject_name",
        "subject_name_cn",
        "barcode_ori",
        "barcode_hand",
        "nm_id",
        "sticker_id",
        "status",
        "status_cn",
        "ready_to_return_dt",
        "completed_dt",
        "expired_dt",
        "return_type",
        "return_type_cn",
        "order_dt",
        "reason",
        "reason_cn",
        "order_id",
        "srid",
        "dst_office_address",
        "dst_office_address_cn",
        "dst_office_id",
    ]
    assert DWDWBReturnDetail.subject_name.comment == "商品品类"
    assert DWDWBReturnDetail.barcode_ori.comment == "原生条形码"
    assert DWDWBReturnDetail.barcode_hand.comment == "手调条形码"


@pytest.mark.asyncio
async def test_upsert_from_ods_maps_both_barcode_types():
    crud = CRUDDWDWBReturnDetail()
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
    assert "TRIM(barcode) REGEXP '^[0-9]{13}$'" in statement
    assert "TRIM(barcode) REGEXP '^[A-Za-z0-9_-]+$'" in statement
    assert "order_dt AS source_order_dt" in statement
    assert "order_dt = source_order_dt" in statement
    assert "order_date" not in statement
    assert "bar_code" not in statement
    assert "ON DUPLICATE KEY UPDATE" in statement
    assert "VALUES(" not in statement
    assert upsert_call.args[1] == {"shop_id": 8}


@pytest.mark.asyncio
async def test_upsert_from_empty_ods_does_not_write():
    crud = CRUDDWDWBReturnDetail()
    db = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    db.execute.return_value = count_result

    result = await crud.upsert_from_ods(db)

    assert result == {"source_count": 0, "affected_rows": 0}
    assert db.execute.await_count == 1
    db.commit.assert_not_awaited()
