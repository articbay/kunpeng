from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from kunpeng.crud.dwd.ozon.sales_funnel import CRUDDWDOzonSalesFunnelDetail
from kunpeng.schemas.ozon_sales_funnel import (
    OzonSalesFunnelExportRequest,
    OzonSalesFunnelFilters,
    OzonSalesFunnelItem,
)
from kunpeng.services.ozon_sales_funnel_service import (
    OZON_SALES_FUNNEL_EXPORT_COLUMNS,
    OzonSalesFunnelService,
)


def _record():
    return SimpleNamespace(
        id=1,
        source_ods_id=10,
        shop_id=7,
        offer_id="offer-1",
        sku=1938260971,
        product_name="Товар",
        product_name_cn="商品",
        category_name="Категория",
        category_name_cn="品类",
        stat_date=date(2026, 8, 25),
        hits_view_search=10,
        hits_view_pdp=20,
        hits_view=30,
        session_view_search=5,
        session_view_pdp=8,
        session_view=13,
        hits_tocart_search=2,
        hits_tocart_pdp=3,
        hits_tocart=5,
        conv_tocart_search=20,
        conv_tocart_pdp=15,
        conv_tocart=16.67,
        ordered_units=2,
        revenue=1000,
        delivered_units=1,
        cancellations=1,
        returns=0,
        position_category=9.5,
        cart_to_order_rate=40,
        has_core_metrics=True,
        has_outcome_metrics=True,
        source_synced_at=datetime(2026, 8, 26, 1, 0),
        create_time=datetime(2026, 8, 26, 1, 1),
        update_time=None,
    )


def test_sales_funnel_item_contains_standard_technical_fields():
    item = OzonSalesFunnelItem.model_validate(_record())
    assert item.source_ods_id == 10
    assert item.create_time == datetime(2026, 8, 26, 1, 1)
    assert item.has_core_metrics is True


def test_dwd_sql_prefers_analytics_sku_name_and_marks_calculated_rate():
    statement = CRUDDWDOzonSalesFunnelDetail._upsert_statement.text
    assert (
        "COALESCE(NULLIF(TRIM(analytics.sku_name), ''), products.product_name)"
        in statement
    )
    assert "analytics.ordered_units / analytics.hits_tocart * 100" in statement


@pytest.mark.asyncio
async def test_export_uses_business_columns_only():
    service = OzonSalesFunnelService()
    db = AsyncMock()
    request = OzonSalesFunnelExportRequest(
        scope="filtered", filters=OzonSalesFunnelFilters(shop_id=7)
    )
    with (
        patch.object(service, "_allowed_shop_ids", AsyncMock(return_value=[7])),
        patch(
            "kunpeng.services.ozon_sales_funnel_service.shop_crud.get_names_by_ids",
            AsyncMock(return_value={7: "测试店铺"}),
        ),
        patch(
            "kunpeng.services.ozon_sales_funnel_service."
            "crud_dwd_ozon_sales_funnel_detail.list_for_export",
            AsyncMock(return_value=[_record()]),
        ),
        patch(
            "kunpeng.services.ozon_sales_funnel_service.build_xlsx",
            return_value=b"xlsx",
        ) as build,
    ):
        result = await service.export_items(db, user_id=1, request=request)

    assert result == b"xlsx"
    assert build.call_args.args[0] == OZON_SALES_FUNNEL_EXPORT_COLUMNS
    exported = build.call_args.args[1][0]
    assert exported["shop_name"] == "测试店铺"
    assert exported["product_name"] == "Товар"
    assert "source_ods_id" in exported
    assert all(
        field != "source_ods_id" for _, field in OZON_SALES_FUNNEL_EXPORT_COLUMNS
    )
