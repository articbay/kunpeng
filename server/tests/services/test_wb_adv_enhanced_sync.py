from unittest.mock import AsyncMock, Mock, patch

import pytest

from kunpeng.services.wb_sync_service import WBSyncService


@pytest.mark.asyncio
async def test_shared_enhanced_sync_refreshes_adverts_before_keywords():
    service = object.__new__(WBSyncService)
    service.db = AsyncMock()
    service.shop = Mock(id=1)
    call_order = []

    def sync_method(name, status="success"):
        async def run(*_args, **_kwargs):
            call_order.append(name)
            return {"status": status, "count": 0}

        return AsyncMock(side_effect=run)

    service.sync_adverts_v2 = sync_method("adverts_v2")
    service.sync_norm_query_bids = sync_method("norm_query_bids")
    service.sync_norm_query_minus = sync_method("norm_query_minus")
    service.sync_norm_query_list = sync_method("norm_query_list")
    service.sync_norm_query_stats = sync_method("norm_query_stats")
    service.sync_promotion_count = sync_method("promotion_count")
    service.sync_bid_recommendations = sync_method("bid_recommendations")
    service.sync_advert_fullstats = sync_method("advert_fullstats")

    with patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_advert_config",
        new=AsyncMock(return_value={"activity_detail": {}, "bid_config": {}}),
    ):
        result = await service._sync_adv_enhanced_shared("2026-08-27", "2026-08-27")

    assert result["status"] == "success"
    assert call_order[0] == "adverts_v2"
    assert call_order[1] == "norm_query_bids"
    assert result["results"]["advert_dwd_config"]["status"] == "success"


def test_enhanced_sync_status_exposes_partial_failure():
    result = WBSyncService._aggregate_sync_status(
        {
            "adverts_v2": {"status": "success"},
            "norm_query_bids": {"status": "error"},
        }
    )

    assert result == "partial_success"


@pytest.mark.asyncio
async def test_sync_adverts_v2_refreshes_advert_product_mapping():
    service = object.__new__(WBSyncService)
    service.db = AsyncMock()
    service.shop = Mock(id=1)
    service._safe_rollback = AsyncMock()
    service.client = Mock()
    service.client.advert = Mock()
    service.client.advert.get_adverts_v2 = AsyncMock(
        return_value={"adverts": [{"id": 10, "nm_settings": [{"nm_id": 20}]}]}
    )
    service.client.__aenter__ = AsyncMock(return_value=service.client)
    service.client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_advert_v2.upsert_many",
        new=AsyncMock(return_value=[object()]),
    ), patch(
        "kunpeng.services.wb_sync_service.crud_ods_wb_advert_product.create_many",
        new=AsyncMock(return_value=[object()]),
    ) as product_upsert:
        result = await service.sync_adverts_v2()

    assert result["status"] == "success"
    assert result["advert_product_count"] == 1
    product_upsert.assert_awaited_once_with(
        service.db,
        adverts_data=[{"id": 10, "nm_settings": [{"nm_id": 20}]}],
        shop_id=1,
    )
