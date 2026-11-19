from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.clients.wildberries import WildberriesReturnsClient
from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


@pytest.mark.asyncio
async def test_returns_client_builds_required_claims_query():
    client = WildberriesReturnsClient("token")
    client._request = AsyncMock(return_value={"claims": [], "total": 0})

    await client.get_claims(is_archive=True, limit=200, offset=400)

    client._request.assert_awaited_once_with(
        "GET",
        "/api/v1/claims",
        params={"is_archive": "true", "limit": 200, "offset": 400},
    )


@pytest.mark.asyncio
async def test_sync_return_claims_filters_window_and_prefers_archived_version():
    moscow = ZoneInfo("Europe/Moscow")
    window_start = datetime(2026, 7, 23, 9, 0, tzinfo=moscow)
    window_end = datetime(2026, 7, 23, 10, 0, tzinfo=moscow)
    shop = Shop(
        id=7,
        name="WB",
        platform="wildberries",
        platform_shop_id="wb-7",
        api_key="token",
        user_id=1,
    )
    service = WBSyncService(AsyncMock(), shop)

    service.client = MagicMock()
    service.client.returns = MagicMock()
    service.client.returns.get_claims = AsyncMock(
        side_effect=[
            {
                "claims": [
                    {
                        "id": "same-claim",
                        "dt": "2026-07-23T09:20:00",
                        "dt_update": "2026-07-23T09:30:00",
                    },
                    {"id": "at-start", "dt": "2026-07-23T09:00:00"},
                    {"id": "too-old", "dt_update": "2026-07-23T08:59:59"},
                    {"id": "at-end", "dt_update": "2026-07-23T10:00:00"},
                ],
                "total": 4,
            },
            {
                "claims": [
                    {
                        "id": "same-claim",
                        "dt": "2026-07-23T09:20:00",
                        "dt_update": "2026-07-23T09:45:00",
                        "status": 3,
                    }
                ],
                "total": 1,
            },
        ]
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_return_claim"
    ) as return_claim_crud:
        return_claim_crud.upsert_many = AsyncMock(return_value=2)
        result = await service.sync_return_claims(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["scanned_count"] == 5
    assert service.client.returns.get_claims.await_count == 2

    claims_data = return_claim_crud.upsert_many.await_args.kwargs["claims_data"]
    claims_by_id = {claim["id"]: claim for claim in claims_data}
    assert set(claims_by_id) == {"same-claim", "at-start"}
    assert claims_by_id["same-claim"]["status"] == 3
    assert claims_by_id["same-claim"]["_is_archive"] is True
    assert claims_by_id["at-start"]["_is_archive"] is False


@pytest.mark.asyncio
async def test_sync_return_claims_returns_error_for_invalid_window():
    moscow = ZoneInfo("Europe/Moscow")
    point = datetime(2026, 7, 23, 10, 0, tzinfo=moscow)
    shop = Shop(
        id=8,
        name="WB",
        platform="wildberries",
        platform_shop_id="wb-8",
        api_key="token",
        user_id=1,
    )
    service = WBSyncService(AsyncMock(), shop)

    result = await service.sync_return_claims(
        window_start=point,
        window_end=point,
    )

    assert result["status"] == "error"
    assert "时间窗口无效" in result["message"]
