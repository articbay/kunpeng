"""Tests for DWD financial report summary API handlers."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from kunpeng.api.v1 import wildberries
from kunpeng.schemas.common import PageResponse


@pytest.mark.asyncio
async def test_list_financial_report_summaries_forwards_filters(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    expected = PageResponse(items=[], total=0, page=1, page_size=20)
    list_summaries = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        wildberries.wb_sales_report_summary_service,
        "list_summaries",
        list_summaries,
    )

    result = await wildberries.list_financial_report_summaries(
        shop_id=8,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        create_date_from=None,
        create_date_to=None,
        report_id=None,
        seller_finance_name="测试",
        report_type=None,
        currency="RUB",
        page=1,
        page_size=20,
        db=Mock(),
        current_user=Mock(id=3),
    )

    assert result is expected
    assert list_summaries.await_args.kwargs["shop_id"] == 8
    assert list_summaries.await_args.kwargs["seller_finance_name"] == "测试"


@pytest.mark.asyncio
async def test_list_financial_report_summaries_rejects_reverse_dates(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    with pytest.raises(HTTPException) as exc_info:
        await wildberries.list_financial_report_summaries(
            shop_id=8,
            date_from=date(2026, 7, 31),
            date_to=date(2026, 7, 1),
            create_date_from=None,
            create_date_to=None,
            report_id=None,
            seller_finance_name=None,
            report_type=None,
            currency=None,
            page=1,
            page_size=20,
            db=Mock(),
            current_user=Mock(id=3),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_export_financial_report_summaries_returns_attachment(monkeypatch):
    monkeypatch.setattr(wildberries, "_ensure_shop_access", AsyncMock())
    export_summaries = AsyncMock(return_value=b"xlsx")
    monkeypatch.setattr(
        wildberries.wb_sales_report_summary_service,
        "export_summaries",
        export_summaries,
    )

    response = await wildberries.export_financial_report_summaries(
        shop_id=8,
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        create_date_from=None,
        create_date_to=None,
        report_id=None,
        seller_finance_name=None,
        report_type=None,
        currency=None,
        db=Mock(),
        current_user=Mock(id=3),
    )

    assert response.body == b"xlsx"
    assert response.media_type.endswith("spreadsheetml.sheet")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="wb_financial_summary_')
    assert "filename*=UTF-8''WB%E8%B4%A2%E5%8A%A1%E6%8A%A5%E5%91%8A" in disposition
