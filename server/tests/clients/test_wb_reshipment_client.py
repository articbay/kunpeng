from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesMarketplaceClient


@pytest.mark.asyncio
async def test_marketplace_client_gets_reshipment_orders_without_parameters():
    client = WildberriesMarketplaceClient("token")
    client._request = AsyncMock(return_value={"orders": []})

    await client.get_reshipment_orders()

    client._request.assert_awaited_once_with(
        "GET",
        "/api/v3/supplies/orders/reshipment",
    )
