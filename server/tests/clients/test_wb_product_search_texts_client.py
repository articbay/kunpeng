"""Wildberries 商品搜索词 API 客户端测试。"""

from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesAnalyticsClient


@pytest.mark.asyncio
async def test_get_sales_funnel_uses_offset_and_endpoint_limiter():
    client = WildberriesAnalyticsClient("test-key")
    client._request = AsyncMock(return_value={"data": {"products": []}})
    client.sales_funnel_rate_limiter.acquire = AsyncMock()

    await client.get_sales_funnel(
        "2026-07-22",
        "2026-07-22",
        limit=1000,
        offset=2000,
    )

    client.sales_funnel_rate_limiter.acquire.assert_awaited_once()
    client._request.assert_awaited_once_with(
        "POST",
        "/api/analytics/v3/sales-funnel/products",
        json={
            "selectedPeriod": {"start": "2026-07-22", "end": "2026-07-22"},
            "limit": 1000,
            "offset": 2000,
        },
        timeout=120.0,
    )


@pytest.mark.asyncio
async def test_get_product_search_texts_uses_expected_payload():
    client = WildberriesAnalyticsClient("test-key")
    client._request_product_search = AsyncMock(return_value={"data": {"items": []}})

    result = await client.get_product_search_texts(
        "2026-07-22",
        "2026-07-23",
        [101, 202],
    )

    assert result == {"data": {"items": []}}
    client._request_product_search.assert_awaited_once_with(
        "/api/v2/search-report/product/search-texts",
        {
            "currentPeriod": {"start": "2026-07-22", "end": "2026-07-23"},
            "nmIds": [101, 202],
            "topOrderBy": "openCard",
            "includeSubstitutedSKUs": True,
            "includeSearchTexts": True,
            "orderBy": {"field": "openCard", "mode": "desc"},
            "limit": 30,
        },
    )


@pytest.mark.asyncio
async def test_get_search_report_products_uses_pagination():
    client = WildberriesAnalyticsClient("test-key")
    client._request_product_search = AsyncMock(return_value={"data": {"products": []}})

    await client.get_search_report_products(
        "2026-07-22",
        "2026-07-23",
        limit=1000,
        offset=1000,
        past_date_from="2026-07-15",
        past_date_to="2026-07-21",
    )

    client._request_product_search.assert_awaited_once_with(
        "/api/v2/search-report/table/details",
        {
            "currentPeriod": {"start": "2026-07-22", "end": "2026-07-23"},
            "pastPeriod": {"start": "2026-07-15", "end": "2026-07-21"},
            "orderBy": {"field": "openCard", "mode": "desc"},
            "positionCluster": "all",
            "includeSubstitutedSKUs": True,
            "includeSearchTexts": True,
            "limit": 1000,
            "offset": 1000,
        },
    )


@pytest.mark.asyncio
async def test_get_product_search_texts_rejects_more_than_fifty_products():
    client = WildberriesAnalyticsClient("test-key")

    with pytest.raises(ValueError, match="1 至 50"):
        await client.get_product_search_texts(
            "2026-07-22",
            "2026-07-23",
            list(range(51)),
        )
