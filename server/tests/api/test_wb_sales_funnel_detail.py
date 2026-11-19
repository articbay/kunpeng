"""Tests for DWD sales funnel detail API handlers."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from kunpeng.api.v1 import wildberries
from kunpeng.schemas.common import PageResponse


@pytest.mark.asyncio
async def test_list_sales_funnel_details_forwards_filters(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    expected = PageResponse(items=[], total=0, page=1, page_size=20)
    list_details = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        wildberries.wb_sales_funnel_detail_service,
        "list_details",
        list_details,
    )

    result = await wildberries.list_sales_funnel_details(
        shop_id=8,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 7),
        nm_id=None,
        vendor_code="ABC",
        title=None,
        subject_name=None,
        brand_name=None,
        page=1,
        page_size=20,
        db=Mock(),
        current_user=Mock(id=3),
    )

    assert result is expected
    assert list_details.await_args.kwargs["shop_id"] == 8
    assert list_details.await_args.kwargs["vendor_code"] == "ABC"


@pytest.mark.asyncio
async def test_list_sales_funnel_details_rejects_reverse_dates(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    with pytest.raises(HTTPException) as exc_info:
        await wildberries.list_sales_funnel_details(
            shop_id=8,
            date_from=date(2026, 7, 7),
            date_to=date(2026, 7, 1),
            nm_id=None,
            vendor_code=None,
            title=None,
            subject_name=None,
            brand_name=None,
            page=1,
            page_size=20,
            db=Mock(),
            current_user=Mock(id=3),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_export_sales_funnel_details_returns_attachment(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    export_details = AsyncMock(return_value=b"xlsx")
    monkeypatch.setattr(
        wildberries.wb_sales_funnel_detail_service,
        "export_details",
        export_details,
    )

    response = await wildberries.export_sales_funnel_details(
        shop_id=8,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 7),
        nm_id=None,
        vendor_code=None,
        title=None,
        subject_name=None,
        brand_name=None,
        db=Mock(),
        current_user=Mock(id=3),
    )

    assert response.body == b"xlsx"
    assert response.media_type.endswith("spreadsheetml.sheet")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="wb_sales_funnel_')
    assert "filename*=UTF-8''WB%E9%94%80%E5%94%AE%E6%BC%8F%E6%96%97" in disposition
