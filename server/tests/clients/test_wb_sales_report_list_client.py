"""Wildberries 财务报表列表 API 客户端测试。"""

from json import JSONDecodeError
from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesFinanceClient


@pytest.mark.asyncio
async def test_get_sales_reports_list_uses_expected_payload():
    client = WildberriesFinanceClient("test-key")
    client._request = AsyncMock(return_value=[])

    result = await client.get_sales_reports_list(
        "2026-07-20",
        "2026-07-26",
        limit=1000,
        offset=0,
        period="weekly",
    )

    assert result == []
    client._request.assert_awaited_once_with(
        "POST",
        "/api/finance/v1/sales-reports/list",
        json={
            "dateFrom": "2026-07-20",
            "dateTo": "2026-07-26",
            "limit": 1000,
            "offset": 0,
            "period": "weekly",
        },
    )


@pytest.mark.asyncio
async def test_get_sales_reports_list_maps_empty_response_to_empty_list():
    client = WildberriesFinanceClient("test-key")
    client._request = AsyncMock(side_effect=JSONDecodeError("empty", "", 0))

    result = await client.get_sales_reports_list(
        "2026-07-20",
        "2026-07-26",
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_sales_reports_detailed_sends_daily_period():
    client = WildberriesFinanceClient("test-key")
    client._request = AsyncMock(return_value=[])

    result = await client.get_sales_reports_detailed(
        "2026-07-20",
        "2026-07-26",
        period="daily",
    )

    assert result == []
    client._request.assert_awaited_once_with(
        "POST",
        "/api/finance/v1/sales-reports/detailed",
        json={
            "dateFrom": "2026-07-20",
            "dateTo": "2026-07-26",
            "limit": 100000,
            "period": "daily",
        },
    )
