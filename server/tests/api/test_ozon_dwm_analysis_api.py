from datetime import date

import pytest
from pydantic import ValidationError

from kunpeng.api.v1 import api_router
from kunpeng.schemas.ozon_goods_daily_analysis import (
    OzonGoodsDailyExportRequest,
    OzonGoodsDailyFilters,
)
from kunpeng.schemas.ozon_order_lifecycle import (
    OzonOrderLifecycleExportRequest,
    OzonOrderLifecycleFilters,
)
from kunpeng.schemas.wb_goods_daily_analysis import (
    WBGoodsDailyExportRequest,
    WBGoodsDailyFilters,
)


def test_dwm_analysis_routes_are_registered():
    paths = {route.path for route in api_router.routes}
    assert {
        "/ozon/goods-daily-analysis",
        "/ozon/goods-daily-analysis/summary",
        "/ozon/goods-daily-analysis/products/{sku}",
        "/ozon/goods-daily-analysis/export",
        "/ozon/order-lifecycle",
        "/ozon/order-lifecycle/summary",
        "/ozon/order-lifecycle/export",
        "/wildberries/goods-daily-analysis",
        "/wildberries/goods-daily-analysis/summary",
        "/wildberries/goods-daily-analysis/products/{nm_id}",
        "/wildberries/goods-daily-analysis/export",
    }.issubset(paths)


@pytest.mark.parametrize(
    "filters_type",
    [OzonGoodsDailyFilters, OzonOrderLifecycleFilters, WBGoodsDailyFilters],
)
def test_dwm_filters_reject_reversed_date_range(filters_type):
    with pytest.raises(ValidationError, match="开始日期不能晚于结束日期"):
        filters_type(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 8, 31),
        )


@pytest.mark.parametrize(
    "request_type",
    [
        OzonGoodsDailyExportRequest,
        OzonOrderLifecycleExportRequest,
        WBGoodsDailyExportRequest,
    ],
)
def test_selected_export_requires_keys(request_type):
    with pytest.raises(ValidationError, match="至少需要选择一条"):
        request_type(scope="selected")


def test_filtered_export_does_not_require_keys():
    goods = OzonGoodsDailyExportRequest(scope="filtered")
    lifecycle = OzonOrderLifecycleExportRequest(scope="filtered")
    wb_goods = WBGoodsDailyExportRequest(scope="filtered")

    assert goods.selected_keys == []
    assert lifecycle.selected_keys == []
    assert wb_goods.selected_keys == []
