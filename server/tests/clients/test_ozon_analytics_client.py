from unittest.mock import AsyncMock

import httpx
import pytest

from kunpeng.clients.base import RateLimitError
from kunpeng.clients.ozon import OZON_ANALYTICS_CORE_METRICS, OzonAnalyticsClient


@pytest.mark.asyncio
async def test_analytics_client_uses_fixed_dimensions_and_requested_sort():
    client = OzonAnalyticsClient("client-id", "api-key")
    client._request = AsyncMock(
        return_value={"result": {"data": [], "totals": [0] * 14}}
    )

    await client.get_analytics_data(
        date_from="2026-08-17",
        date_to="2026-08-23",
        metrics=OZON_ANALYTICS_CORE_METRICS,
        sort_key="revenue",
        offset=1000,
    )

    client._request.assert_awaited_once()
    method, path = client._request.await_args.args
    payload = client._request.await_args.kwargs["json"]
    assert (method, path) == ("POST", "/v1/analytics/data")
    assert payload["dimension"] == ["sku", "day"]
    assert payload["metrics"] == OZON_ANALYTICS_CORE_METRICS
    assert payload["sort"] == [{"key": "revenue", "order": "DESC"}]
    assert payload["limit"] == 1000
    assert payload["offset"] == 1000


@pytest.mark.asyncio
async def test_analytics_client_rejects_more_than_fourteen_metrics():
    client = OzonAnalyticsClient("client-id", "api-key")
    with pytest.raises(ValueError, match="between 1 and 14"):
        await client.get_analytics_data(
            date_from="2026-08-23",
            date_to="2026-08-23",
            metrics=[f"metric_{index}" for index in range(15)],
        )


@pytest.mark.asyncio
async def test_analytics_client_waits_and_retries_rate_limit(monkeypatch):
    client = OzonAnalyticsClient("client-id", "api-key")
    request = httpx.Request("POST", "https://api-seller.ozon.ru/v1/analytics/data")
    response = httpx.Response(429, headers={"Retry-After": "70"}, request=request)
    client.post = AsyncMock(
        side_effect=[RateLimitError("limited", response), {"result": {}}]
    )
    sleep = AsyncMock()
    monkeypatch.setattr("kunpeng.clients.ozon.asyncio.sleep", sleep)

    result = await client.get_analytics_data(
        date_from="2026-08-23",
        date_to="2026-08-23",
        metrics=["revenue"],
    )

    assert result == {"result": {}}
    assert client.post.await_count == 2
    sleep.assert_awaited_once_with(70.0)
