from decimal import Decimal

from kunpeng.crud.ods.ozon.fbo_postings import crud_ods_ozon_fbo_posting_product
from kunpeng.crud.ods.ozon.postings import (
    crud_ods_ozon_fbs_posting,
    crud_ods_ozon_fbs_posting_product,
)
from kunpeng.crud.ods.ozon.realization import (
    crud_ods_ozon_finance_realization_header,
    crud_ods_ozon_finance_realization_row,
)
from kunpeng.crud.ods.ozon.reviews import crud_ods_ozon_review
from kunpeng.crud.ods.ozon.utils import parse_datetime_field


def test_ozon_datetime_parser_rejects_epoch_placeholder() -> None:
    assert parse_datetime_field("1970-01-01T00:00:00Z") is None


def test_fbs_posting_prefers_v4_top_level_fields() -> None:
    item = {
        "posting_number": "12345-0001-1",
        "tpl_integration_type": "ozon",
        "destination_place_id": 42,
        "destination_place_name": "Москва",
        "prr_option": {"code": "lift"},
        "analytics_data": {
            "tpl_integration_type": "legacy",
            "destination_place_id": 1,
            "destination_place_name": "legacy",
        },
    }

    data = crud_ods_ozon_fbs_posting._extract_item_data(item, shop_id=2)

    assert data["tpl_integration_type"] == "ozon"
    assert data["destination_place_id"] == 42
    assert data["destination_place_name"] == "Москва"
    assert data["prr_option"] == "lift"


def test_fbs_product_extracts_price_object_and_imei() -> None:
    item = {
        "sku": 2098562954,
        "price": {"amount": "528.00", "currency": "RUB"},
        "imei": ["123456789012345"],
    }

    data = crud_ods_ozon_fbs_posting_product._extract_item_data(
        item, shop_id=2, posting_number="12345-0001-1"
    )

    assert data["price_amount"] == Decimal("528.00")
    assert data["price_currency"] == "RUB"
    assert data["imei"] == ["123456789012345"]


def test_fbo_product_supports_price_object_and_legacy_scalar() -> None:
    current = crud_ods_ozon_fbo_posting_product._extract_item_data(
        {
            "sku": 2098562954,
            "price": {"amount": "528.00", "currency": "RUB"},
        },
        shop_id=2,
        posting_number="12345-0001-1",
    )
    legacy = crud_ods_ozon_fbo_posting_product._extract_item_data(
        {"sku": 2098562954, "price": "529.00", "currency_code": "RUB"},
        shop_id=2,
        posting_number="12345-0001-2",
    )

    assert current["price"] == Decimal("528.00")
    assert current["currency_code"] == "RUB"
    assert legacy["price"] == Decimal("529.00")
    assert legacy["currency_code"] == "RUB"


def test_review_extracts_flat_uuid_response() -> None:
    item = {
        "id": "0198054a-b549-70cd-860c-12194d34682f",
        "sku": 2098671446,
        "text": "很好用",
        "rating": 5,
        "published_at": "2025-07-13T19:37:19.687615Z",
    }

    data = crud_ods_ozon_review._extract_item_data(item, shop_id=2)

    assert data["review_id"] == item["id"]
    assert data["sku"] == item["sku"]
    assert data["text"] == item["text"]
    assert str(data["published_at"]).startswith("2025-07-13")


def test_review_keeps_nested_response_compatibility() -> None:
    item = {
        "id": "legacy-review",
        "product": {"sku": 123, "name": "商品A"},
        "data": {"text": "旧结构"},
        "rating": 4,
    }

    data = crud_ods_ozon_review._extract_item_data(item, shop_id=2)

    assert data["sku"] == 123
    assert data["product_name"] == "商品A"
    assert data["text"] == "旧结构"


def test_realization_header_extracts_wrapped_response() -> None:
    item = {
        "header": {
            "header": {
                "num": "RPT-2026-06",
                "doc_date": "2026-06-30",
                "contract_num": "C-001",
                "currency_sys_name": "RUB",
                "payer_name": "Payer Ltd",
                "rcv_kpp": "444",
            },
            "rows": [],
        }
    }

    data = crud_ods_ozon_finance_realization_header._extract_item_data(
        item,
        shop_id=2,
    )

    assert data["report_number"] == "RPT-2026-06"
    assert str(data["doc_date"]) == "2026-06-30"
    assert data["contract_number"] == "C-001"
    assert data["currency"] == "RUB"
    assert data["payer_name"] == "Payer Ltd"
    assert data["receiver_kpp"] == "444"


def test_realization_row_extracts_nested_commissions() -> None:
    item = {
        "item": {
            "sku": 2087643175,
            "name": "商品名称",
            "barcode": "TG-C029014",
            "offer_id": "TG-C029014",
        },
        "rowNumber": 1,
        "commission_ratio": 0.42,
        "seller_price_per_instance": 900,
        "delivery_commission": {
            "amount": 427.62,
            "quantity": 1,
            "standard_fee": 378,
            "bonus": 468.1,
            "bank_coinvestment": 4.28,
            "total": 522,
            "price_per_instance": 427.62,
        },
        "return_commission": None,
    }

    data = crud_ods_ozon_finance_realization_row._extract_item_data(
        item,
        shop_id=2,
        header_id=10,
    )

    assert data["row_number"] == 1
    assert data["sku"] == 2087643175
    assert data["sold_amount"] == Decimal("427.62")
    assert data["sold_total"] == Decimal("522")
    assert data["is_return"] is False
    assert data["return_amount"] is None
