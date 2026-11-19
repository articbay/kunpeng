from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.wildberries import WildberriesAdvertClient


@pytest.mark.asyncio
async def test_norm_query_bids_extracts_nm_settings_and_batches_requests():
    client = WildberriesAdvertClient("token")
    adverts = {
        "adverts": [
            {
                "id": 101,
                "nm_settings": [{"nm_id": nm_id} for nm_id in range(1, 102)],
            }
        ]
    }
    client._request = AsyncMock(
        side_effect=[
            adverts,
            {"bids": [{"advert_id": 101, "nm_id": 1, "norm_query": "one"}]},
            {"bids": [{"advert_id": 101, "nm_id": 101, "norm_query": "last"}]},
        ]
    )

    result = await client.get_norm_query_bids()

    assert len(result) == 2
    assert client._request.await_count == 3
    first_payload = client._request.await_args_list[1].kwargs["json"]
    second_payload = client._request.await_args_list[2].kwargs["json"]
    assert len(first_payload["items"]) == 100
    assert len(second_payload["items"]) == 1
    assert all(item["nm_id"] > 0 for item in first_payload["items"])
    assert client._request.await_args_list[1].args[:2] == (
        "POST",
        "/adv/v0/normquery/get-bids",
    )


@pytest.mark.asyncio
async def test_norm_query_list_uses_camel_case_items_from_nm_settings():
    client = WildberriesAdvertClient("token")
    client._request = AsyncMock(
        side_effect=[
            {"adverts": [{"id": 201, "nm_settings": [{"nm_id": 301}]}]},
            {"items": []},
        ]
    )

    result = await client.get_norm_query_list()

    assert result == []
    assert client._request.await_args_list[1].kwargs["json"] == {
        "items": [{"advertId": 201, "nmId": 301}]
    }


@pytest.mark.asyncio
async def test_norm_query_stats_uses_v1_and_flattens_daily_stats():
    client = WildberriesAdvertClient("token")
    client._request = AsyncMock(
        side_effect=[
            {"adverts": [{"id": 401, "nm_settings": [{"nm_id": 501}]}]},
            {
                "items": [
                    {
                        "advertId": 401,
                        "nmId": 501,
                        "dailyStats": [
                            {
                                "date": "2026-08-27",
                                "stat": {
                                    "normQuery": "keyword",
                                    "views": 10,
                                    "spend": 12.5,
                                },
                            }
                        ],
                    }
                ]
            },
        ]
    )

    result = await client.get_norm_query_stats("2026-08-27", "2026-08-27")

    assert result == [
        {
            "advertId": 401,
            "nmId": 501,
            "date": "2026-08-27",
            "stat": {
                "normQuery": "keyword",
                "views": 10,
                "spend": 12.5,
            },
        }
    ]
    assert client._request.await_args_list[1].args[:2] == (
        "POST",
        "/adv/v1/normquery/stats",
    )
    assert client._request.await_args_list[1].kwargs["json"]["items"] == [
        {"advertId": 401, "nmId": 501}
    ]


@pytest.mark.asyncio
async def test_norm_query_request_stops_when_adverts_have_no_products():
    client = WildberriesAdvertClient("token")
    client._request = AsyncMock(return_value={"adverts": [{"id": 601}]})

    result = await client.get_norm_query_minus()

    assert result == []
    client._request.assert_awaited_once_with("GET", "/api/advert/v2/adverts", params={})
