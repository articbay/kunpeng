from kunpeng.crud.dwd.ozon.advert_efficiency import CRUDDWDOzonAdvertEfficiencyDetail
from kunpeng.services.ozon_advert_efficiency_service import (
    OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS,
    PAYMENT_TYPE_DISPLAY,
    PLACEMENT_DISPLAY,
    _localized_code,
)


def test_export_headers_follow_confirmed_reference_order():
    assert [label for label, _ in OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS] == [
        "店铺ID",
        "店铺名称",
        "统计日期",
        "SKU",
        "商品名称",
        "商品名称（中文）",
        "品类名称",
        "品类名称（中文）",
        "工具",
        "投放位置",
        "广告活动 ID",
        "广告活动名称",
        "费用，₽",
        "广告费用份额, %",
        "销售额，₽",
        "订单，个",
        "CTR, %",
        "展现量",
        "点击次数",
        "添加到购物车",
        "添加到购物车的转化率， %",
        "单笔费用，₽",
        "每次点击成本，₽",
    ]


def test_dwd_sql_uses_daily_grain_latest_product_and_safe_ratios():
    sql = str(CRUDDWDOzonAdvertEfficiencyDetail._upsert_statement)
    assert "ROW_NUMBER() OVER" in sql
    assert "PARTITION BY shop_id, sku" in sql
    assert "daily.stat_date = stats.stat_date" in sql
    assert "stats.money_spent / stats.orders_money * 100" in sql
    assert "stats.clicks / stats.views * 100" in sql
    assert "stats.to_cart / stats.clicks * 100" in sql
    assert "WHEN COALESCE(stats.orders, 0) = 0 THEN NULL" in sql


def test_known_advert_codes_are_localized_without_losing_unknown_values():
    assert _localized_code("CPC", PAYMENT_TYPE_DISPLAY) == "按点击付费"
    assert _localized_code("CPO", PAYMENT_TYPE_DISPLAY) == "按订单付费"
    assert _localized_code("PLACEMENT_TOP_PROMOTION", PLACEMENT_DISPLAY) == "顶部推广"
    assert _localized_code("NEW_CODE", PAYMENT_TYPE_DISPLAY) == "NEW_CODE"
