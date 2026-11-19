from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesMarketplaceClient


@pytest.mark.asyncio
async def test_marketplace_client_gets_supply_page_with_cursor():
    client = WildberriesMarketplaceClient("token")
    client._request = AsyncMock(return_value={"next": 42, "supplies": []})

    await client.get_supplies(limit=1000, next_=17)

    client._request.assert_awaited_once_with(
        "GET",
        "/api/v3/supplies",
        params={"limit": 1000, "next": 17},
    )


@pytest.mark.asyncio
async def test_marketplace_client_validates_supply_pagination():
    client = WildberriesMarketplaceClient("token")

    with pytest.raises(ValueError, match="between 1 and 1000"):
        await client.get_supplies(limit=1001)
    with pytest.raises(ValueError, match="non-negative"):
        await client.get_supplies(next_=-1)
