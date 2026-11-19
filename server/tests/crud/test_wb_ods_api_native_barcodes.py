from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.ods.wildberries.finance import CRUDODSWBSalesReport
from kunpeng.crud.ods.wildberries.funnel import CRUDODSWBGoodsReturn
from kunpeng.crud.ods.wildberries.marketplace import CRUDODSWBMarketplaceOrder
from kunpeng.crud.ods.wildberries.new_orders import CRUDODSWBNewOrder
from kunpeng.crud.ods.wildberries.sales import (
    CRUDODSWBSupplierOrder,
    CRUDODSWBSupplierSale,
)
from kunpeng.models.ods.wildberries.finance import ODSWBSalesReport
from kunpeng.models.ods.wildberries.marketplace import ODSWBMarketplaceOrder
from kunpeng.models.ods.wildberries.new_orders import ODSWBNewOrder
from kunpeng.models.ods.wildberries.returns import ODSWBGoodsReturn
from kunpeng.models.ods.wildberries.sales import ODSWBSupplierOrder, ODSWBSupplierSale


def test_wb_ods_models_keep_api_native_barcode_fields():
    scalar_models = {
        ODSWBSupplierSale: "barcode",
        ODSWBSupplierOrder: "barcode",
        ODSWBSalesReport: "sku",
        ODSWBGoodsReturn: "barcode",
    }
    array_models = {
        ODSWBMarketplaceOrder: "skus",
        ODSWBNewOrder: "skus",
    }

    for model, native_column in {**scalar_models, **array_models}.items():
        columns = model.__table__.columns
        assert native_column in columns
        assert "barcode_ori" not in columns
        assert "barcode_hand" not in columns


def test_finance_and_new_order_extractors_preserve_api_values():
    finance = CRUDODSWBSalesReport(ODSWBSalesReport)
    finance_data = finance._extract_item_data(
        {
            "dateFrom": "2026-08-01",
            "dateTo": "2026-08-07",
            "rrdId": 1,
            "sku": "TG-HC02904",
        },
        shop_id=8,
    )
    assert finance_data["sku"] == "TG-HC02904"
    assert "barcode_ori" not in finance_data
    assert "barcode_hand" not in finance_data

    new_order = CRUDODSWBNewOrder()
    skus = ["2044420598851", "TG-HC02904"]
    new_order_data = new_order._extract_fields({"skus": skus})
    assert new_order_data["skus"] == skus
    assert "barcode_ori" not in new_order_data
    assert "barcode_hand" not in new_order_data


@pytest.mark.asyncio
async def test_marketplace_order_preserves_complete_skus_array(monkeypatch):
    crud = CRUDODSWBMarketplaceOrder()
    monkeypatch.setattr(crud, "get_by_order_id", AsyncMock(return_value=None))
    db = AsyncMock()
    db.add = Mock()
    skus = ["2044420598851", "TG-HC02904"]

    result = await crud.create_or_update(
        db,
        {"id": 1001, "skus": skus},
        shop_id=8,
    )

    assert result.skus == skus
    db.add.assert_called_once_with(result)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("crud", "payload_name", "payload", "expected_field"),
    [
        (
            CRUDODSWBSupplierSale(ODSWBSupplierSale),
            "sales_data",
            {"srid": "sale-1", "barcode": "TG-HC02904"},
            "barcode",
        ),
        (
            CRUDODSWBSupplierOrder(ODSWBSupplierOrder),
            "orders_data",
            {"srid": "order-1", "barcode": "2044420598851"},
            "barcode",
        ),
        (
            CRUDODSWBGoodsReturn(ODSWBGoodsReturn),
            "returns_data",
            {"srid": "return-1", "barcode": "2044420598851"},
            "barcode",
        ),
    ],
)
async def test_scalar_ods_crud_preserves_api_barcode(
    monkeypatch, crud, payload_name, payload, expected_field
):
    monkeypatch.setattr(crud, "_get_existing", AsyncMock(return_value=None))
    db = AsyncMock()
    db.add = Mock()

    rows = await crud.create_many(
        db,
        **{payload_name: [payload]},
        shop_id=8,
    )

    assert getattr(rows[0], expected_field) == payload[expected_field]
    assert not hasattr(rows[0], "barcode_ori")
    assert not hasattr(rows[0], "barcode_hand")


@pytest.mark.asyncio
async def test_supplier_sale_preserves_api_uppercase_id_fields(monkeypatch):
    crud = CRUDODSWBSupplierSale(ODSWBSupplierSale)
    monkeypatch.setattr(crud, "_get_existing", AsyncMock(return_value=None))
    db = AsyncMock()
    db.add = Mock()

    rows = await crud.create_many(
        db,
        sales_data=[
            {
                "srid": "sale-1",
                "saleID": "S25071036298",
                "incomeID": 123,
            }
        ],
        shop_id=8,
    )

    assert rows[0].sale_id == "S25071036298"
    assert rows[0].income_id == 123
