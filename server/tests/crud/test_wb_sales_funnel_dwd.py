"""Tests for the Wildberries sales funnel ODS-to-DWD mapping."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.dwd.wildberries.funnel import (
    FUNNEL_BUSINESS_FIELDS,
    crud_dwd_wb_sales_funnel_detail,
)
from kunpeng.models.ods.wildberries.funnel import ODSWBSalesFunnel
from kunpeng.services.wb_dwd_service import wb_dwd_service


def _source(
    *,
    source_id: int,
    shop_id: int,
    nm_id: int,
) -> ODSWBSalesFunnel:
    source = ODSWBSalesFunnel(
        shop_id=shop_id,
        date_from=date(2026, 7, 29),
        date_to=date(2026, 7, 29),
        nm_id=nm_id,
        vendor_code="vendor-code",
        title="Product title",
        subject_name="Subject",
        brand_name="Brand",
        tags=[{"id": 1, "name": "tag"}],
        product_rating=5,
        feedback_rating=Decimal("4.80"),
        open_count=100,
        cart_count=20,
        add_to_wishlist=8,
        order_count=10,
        buyout_count=7,
        cancel_count=1,
        add_to_cart_percent=Decimal("20.00"),
        cart_to_order_percent=Decimal("50.00"),
        buyout_percent=Decimal("70.00"),
        order_sum=Decimal("1000.00"),
        buyout_sum=Decimal("700.00"),
        cancel_sum=Decimal("100.00"),
        row_data={},
    )
    source.id = source_id
    return source


def _mock_db(existing: list | None = None) -> Mock:
    db = Mock()
    db.execute = AsyncMock(
        return_value=Mock(
            scalars=Mock(
                return_value=Mock(all=Mock(return_value=existing or [])),
            ),
        )
    )
    db.add = Mock()
    db.flush = AsyncMock()
    return db


def test_mapping_contains_exactly_21_business_fields():
    assert FUNNEL_BUSINESS_FIELDS == (
        "vendor_code",
        "nm_id",
        "title",
        "subject_name",
        "brand_name",
        "tags",
        "product_rating",
        "feedback_rating",
        "date_from",
        "open_count",
        "cart_count",
        "add_to_wishlist",
        "order_count",
        "buyout_count",
        "cancel_count",
        "add_to_cart_percent",
        "cart_to_order_percent",
        "buyout_percent",
        "order_sum",
        "buyout_sum",
        "cancel_sum",
    )


@pytest.mark.asyncio
async def test_upsert_maps_fields_and_updates_existing_business_key():
    source = _source(source_id=9, shop_id=8, nm_id=123456)
    first_db = _mock_db()

    first_stats = await crud_dwd_wb_sales_funnel_detail.upsert_source_batch(
        first_db,
        sources=[source],
    )
    created = first_db.add.call_args.args[0]

    assert first_stats == {"created": 1, "updated": 0}
    assert created.source_ods_id == 9
    assert created.shop_id == 8
    assert created.date_to == date(2026, 7, 29)
    assert created.open_count == 100
    assert created.buyout_sum == Decimal("700.00")

    updated_source = _source(source_id=9, shop_id=8, nm_id=123456)
    updated_source.open_count = 150
    second_db = _mock_db([created])

    second_stats = await crud_dwd_wb_sales_funnel_detail.upsert_source_batch(
        second_db,
        sources=[updated_source],
    )

    assert second_stats == {"created": 0, "updated": 1}
    second_db.add.assert_not_called()
    assert created.open_count == 150


@pytest.mark.asyncio
async def test_service_filters_source_scan_by_shop(monkeypatch):
    source = _source(source_id=9, shop_id=8, nm_id=123456)
    get_source_batch = AsyncMock(side_effect=[[source], []])
    upsert_source_batch = AsyncMock(return_value={"created": 1, "updated": 0})
    monkeypatch.setattr(
        crud_dwd_wb_sales_funnel_detail,
        "get_source_batch",
        get_source_batch,
    )
    monkeypatch.setattr(
        crud_dwd_wb_sales_funnel_detail,
        "upsert_source_batch",
        upsert_source_batch,
    )
    db = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    stats = await wb_dwd_service.sync_sales_funnel_detail(
        db,
        shop_id=8,
        batch_size=10,
    )

    assert stats == {"scanned": 1, "created": 1, "updated": 0}
    assert get_source_batch.await_args_list[0].kwargs == {
        "after_id": 0,
        "batch_size": 10,
        "shop_id": 8,
    }
    assert get_source_batch.await_args_list[1].kwargs == {
        "after_id": 9,
        "batch_size": 10,
        "shop_id": 8,
    }
