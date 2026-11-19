"""Ozon 应计费用明细拆解单元测试

覆盖 build_fee_lines：把 by-day 的真实嵌套结构拆成"一条费用一行"。
纯函数逻辑，不依赖数据库。
"""
from decimal import Decimal
from datetime import date

from kunpeng.crud.ods.ozon.finance import crud_ods_ozon_accrual_fee


def _index(lines, fee_source, type_id=None):
    for l in lines:
        if l["fee_source"] == fee_source and (type_id is None or l["type_id"] == type_id):
            return l
    return None


def test_posting_splits_revenue_commission_and_services():
    """POSTING 拆成：营收 + 销售佣金 + N 条物流服务费"""
    accrual = {
        "accrual_id": 52796360085,
        "accrued_category": "POSTING",
        "unit_number": "93912282-0092-1",
        "total_amount": {"amount": "280.09", "currency": "RUB"},
        "posting": {
            "delivery_schema": "Fbs",
            "products": [{
                "sku": 2089164658,
                "commission": {
                    "sale_amount": {"amount": "650", "currency": "RUB"},
                    "sale_commission": {"amount": "-273", "currency": "RUB"},
                    "seller_price": {"amount": "590", "currency": "RUB"},
                    "commission_ratio": 'value:"0.420000"',
                },
                "delivery": {"services": [
                    {"type_id": 32, "accrued": {"amount": "-72", "currency": "RUB"}},
                    {"type_id": 16, "accrued": {"amount": "-20", "currency": "RUB"}},
                    {"type_id": 29, "accrued": {"amount": "-4.91", "currency": "RUB"}},
                ]},
            }],
        },
    }
    lines = crud_ods_ozon_accrual_fee.build_fee_lines(
        accrual, shop_id=2, accrual_id=52796360085, accrual_date="2026-06-02"
    )
    assert len(lines) == 5  # 营收 + 佣金 + 3条服务费
    rev = _index(lines, "revenue")
    assert rev["type_id"] == -1 and rev["amount"] == Decimal("650")
    assert rev["delivery_schema"] == "Fbs"
    assert rev["seller_price"] == Decimal("590")
    assert rev["commission_ratio"] == Decimal("0.420000")
    com = _index(lines, "sale_commission")
    assert com["type_id"] == 69 and com["amount"] == Decimal("-273")
    svc = _index(lines, "posting_service", 32)
    assert svc["amount"] == Decimal("-72") and svc["currency"] == "RUB"
    # 明细金额合计 == total_amount
    assert round(sum(l["amount"] for l in lines), 2) == Decimal("280.09")
    # 应计日期被解析成 date
    assert rev["accrual_date"] == date(2026, 6, 2)


def test_item_splits_each_fee_line():
    """ITEM 拆成 N 条商品费用行"""
    accrual = {
        "accrual_id": 52796547660,
        "accrued_category": "ITEM",
        "unit_number": "93912282-0092-1",
        "total_amount": {"amount": "-8.45", "currency": "RUB"},
        "item_fees": {"fees": [
            {"sku": 2089164658, "fees": [
                {"type_id": 95, "accrued": {"amount": "-8.45", "currency": "RUB"}}
            ]}
        ]},
    }
    lines = crud_ods_ozon_accrual_fee.build_fee_lines(
        accrual, shop_id=2, accrual_id=52796547660, accrual_date="2026-06-02"
    )
    assert len(lines) == 1
    fee = lines[0]
    assert fee["fee_source"] == "item_fee"
    assert fee["type_id"] == 95 and fee["sku"] == 2089164658
    assert fee["amount"] == Decimal("-8.45")


def test_non_item_single_line_with_null_sku():
    """NON_ITEM 拆成 1 条非商品费用行，sku 为 None"""
    accrual = {
        "accrual_id": 52796395615,
        "accrued_category": "NON_ITEM",
        "unit_number": "93912282-0092-1",
        "total_amount": {"amount": "-100", "currency": "RUB"},
        "non_item_fee": {"type_id": 94, "accrued": {"amount": "-100", "currency": "RUB"}},
    }
    lines = crud_ods_ozon_accrual_fee.build_fee_lines(
        accrual, shop_id=2, accrual_id=52796395615, accrual_date="2026-06-02"
    )
    assert len(lines) == 1
    fee = lines[0]
    assert fee["fee_source"] == "non_item_fee"
    assert fee["type_id"] == 94 and fee["sku"] is None
    assert fee["amount"] == Decimal("-100")


def test_type_name_redundancy_from_dict():
    """type_dict 命中时冗余 type_name/type_desc；营收行固定 Revenue"""
    accrual = {
        "accrual_id": 1,
        "accrued_category": "POSTING",
        "posting": {"delivery_schema": "Fbo", "products": [{
            "sku": 1,
            "commission": {"sale_amount": {"amount": "100", "currency": "RUB"}},
            "delivery": {"services": [
                {"type_id": 32, "accrued": {"amount": "-10", "currency": "RUB"}}
            ]},
        }]},
    }
    type_dict = {32: {"name": "Logistic", "description": "Логистика"}}
    lines = crud_ods_ozon_accrual_fee.build_fee_lines(
        accrual, shop_id=2, accrual_id=1, accrual_date="2026-06-02", type_dict=type_dict
    )
    svc = _index(lines, "posting_service", 32)
    assert svc["type_name"] == "Logistic" and svc["type_desc"] == "Логистика"
    rev = _index(lines, "revenue")
    assert rev["type_name"] == "Revenue"


def test_bonus_coinvestment_not_emitted():
    """bonus/coinvestment 不计入 total_amount，不产生费用行"""
    accrual = {
        "accrual_id": 1,
        "accrued_category": "POSTING",
        "posting": {"products": [{
            "sku": 1,
            "commission": {
                "sale_amount": {"amount": "100", "currency": "RUB"},
                "sale_commission": {"amount": "-40", "currency": "RUB"},
                "bonus": {"amount": "50", "currency": "RUB"},
                "coinvestment": {"amount": "3", "currency": "RUB"},
            },
        }]},
    }
    lines = crud_ods_ozon_accrual_fee.build_fee_lines(
        accrual, shop_id=2, accrual_id=1, accrual_date="2026-06-02"
    )
    sources = sorted(l["fee_source"] for l in lines)
    assert sources == ["revenue", "sale_commission"]
