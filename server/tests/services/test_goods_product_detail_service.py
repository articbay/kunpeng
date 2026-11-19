from datetime import date
from unittest.mock import AsyncMock

import pytest

from kunpeng.crud import shop_crud
from kunpeng.crud.dwm.ozon.goods_daily_analysis import (
    crud_dwm_ozon_goods_daily_analysis,
)
from kunpeng.crud.dwm.wildberries.goods_daily_analysis import (
    crud_dwm_wb_goods_daily_analysis,
)
from kunpeng.schemas.ozon_goods_daily_analysis import OzonGoodsDailyFilters
from kunpeng.schemas.wb_goods_daily_analysis import WBGoodsDailyFilters
from kunpeng.services.ozon_goods_daily_analysis_service import (
    ozon_goods_daily_analysis_service,
)
from kunpeng.services.wb_goods_daily_analysis_service import (
    wb_goods_daily_analysis_service,
)


def metrics() -> dict:
    return {
        "sales_amount": 100,
        "order_qty": 5,
        "return_qty": 1,
        "return_rate": 0.2,
        "ad_spend": 10,
        "ad_attributed_sales": 40,
        "ad_roas": 4,
    }


@pytest.mark.asyncio
async def test_ozon_product_detail_keeps_permissions_and_adds_shop_name(monkeypatch):
    detail_query = AsyncMock(
        return_value={
            "sku": 123,
            "offer_id": "offer",
            "product_name": "name",
            "product_name_cn": "中文名",
            "category_name": None,
            "category_name_cn": None,
            "period_from": date(2026, 8, 1),
            "period_to": date(2026, 8, 31),
            "metrics": metrics(),
            "shops": [{"shop_id": 4, "metrics": metrics()}],
        }
    )
    monkeypatch.setattr(
        ozon_goods_daily_analysis_service, "_allowed", AsyncMock(return_value=[4])
    )
    monkeypatch.setattr(
        crud_dwm_ozon_goods_daily_analysis, "get_product_detail", detail_query
    )
    monkeypatch.setattr(
        shop_crud, "get_names_by_ids", AsyncMock(return_value={4: "Ozon店"})
    )

    result = await ozon_goods_daily_analysis_service.product_detail(
        AsyncMock(),
        user_id=9,
        sku=123,
        filters=OzonGoodsDailyFilters(date_from=date(2026, 8, 1)),
    )

    assert result.shops[0].shop_name == "Ozon店"
    assert detail_query.await_args.kwargs["allowed_shop_ids"] == [4]
    assert detail_query.await_args.kwargs["sku"] == 123


@pytest.mark.asyncio
async def test_wb_product_detail_keeps_permissions_and_adds_shop_name(monkeypatch):
    detail_query = AsyncMock(
        return_value={
            "nm_id": 456,
            "vendor_code": "vendor",
            "product_title": "name",
            "product_title_cn": None,
            "brand_name": None,
            "subject_name": "category",
            "subject_name_cn": None,
            "period_from": date(2026, 8, 1),
            "period_to": date(2026, 8, 31),
            "metrics": metrics(),
            "shops": [{"shop_id": 8, "metrics": metrics()}],
        }
    )
    monkeypatch.setattr(
        wb_goods_daily_analysis_service, "_allowed", AsyncMock(return_value=[8])
    )
    monkeypatch.setattr(
        crud_dwm_wb_goods_daily_analysis, "get_product_detail", detail_query
    )
    monkeypatch.setattr(
        shop_crud, "get_names_by_ids", AsyncMock(return_value={8: "WB店"})
    )

    result = await wb_goods_daily_analysis_service.product_detail(
        AsyncMock(),
        user_id=9,
        nm_id=456,
        filters=WBGoodsDailyFilters(date_to=date(2026, 8, 31)),
    )

    assert result.shops[0].shop_name == "WB店"
    assert detail_query.await_args.kwargs["allowed_shop_ids"] == [8]
    assert detail_query.await_args.kwargs["nm_id"] == 456
