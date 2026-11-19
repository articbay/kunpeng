"""Wildberries 区域销售 API 客户端测试。"""

from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesAnalyticsClient


@pytest.mark.asyncio
async def test_get_region_sales_uses_expected_endpoint_and_dates():
    client = WildberriesAnalyticsClient("test-key")
    client._request = AsyncMock(return_value={"report": []})

    result = await client.get_region_sales("2026-07-22", "2026-07-23")

    assert result == {"report": []}
    client._request.assert_awaited_once_with(
        "GET",
        "/api/v1/analytics/region-sale",
        params={
            "dateFrom": "2026-07-22",
            "dateTo": "2026-07-23",
        },
    )
