from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesMarketplaceClient


@pytest.mark.asyncio
async def test_marketplace_client_posts_order_ids_for_metadata():
    client = WildberriesMarketplaceClient("token")
    client._request = AsyncMock(return_value={"orders": []})

    await client.get_orders_metadata([123, 456])

    client._request.assert_awaited_once_with(
        "POST",
        "/api/marketplace/v3/orders/meta",
        json={"orders": [123, 456]},
    )


@pytest.mark.asyncio
async def test_marketplace_client_rejects_more_than_100_metadata_order_ids():
    client = WildberriesMarketplaceClient("token")

    with pytest.raises(ValueError, match="at most 100"):
        await client.get_orders_metadata(list(range(101)))
