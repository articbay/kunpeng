from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from kunpeng.clients.ozon import (
    OZON_ANALYTICS_CORE_METRICS,
    OZON_ANALYTICS_OUTCOME_METRICS,
    OzonClient,
)
from kunpeng.services.ozon_sync_service import (
    OzonSyncService,
    parse_ozon_analytics_page,
)


def _response(metrics, values, totals=None):
    return {
        "result": {
            "data": [
                {
                    "dimensions": [
                        {"id": "1938260971", "name": "Product"},
                        {"id": "2026-08-23", "name": ""},
                    ],
                    "metrics": values,
                }
            ],
            "totals": totals if totals is not None else values,
        },
        "timestamp": "2026-08-24 07:05:00",
    }


def test_parse_analytics_page_labels_positional_metrics():
    values = list(range(len(OZON_ANALYTICS_CORE_METRICS)))
    parsed = parse_ozon_analytics_page(
        _response(OZON_ANALYTICS_CORE_METRICS, values),
        OZON_ANALYTICS_CORE_METRICS,
    )

    row = parsed["rows"][(1938260971, date(2026, 8, 23))]
    assert row["sku_name"] == "Product"
    assert row["metrics"]["revenue"] == 0
    assert row["metrics"]["conv_tocart"] == 13
    assert parsed["totals"]["ordered_units"] == 1


def test_parse_analytics_page_rejects_metric_length_mismatch():
    response = _response(OZON_ANALYTICS_CORE_METRICS, [1, 2])
    response["result"]["totals"] = [0] * len(OZON_ANALYTICS_CORE_METRICS)
    with pytest.raises(ValueError, match="returned totals"):
        parse_ozon_analytics_page(response, OZON_ANALYTICS_CORE_METRICS)


def test_parse_analytics_page_accepts_permission_truncated_metric_prefix():
    response = _response(OZON_ANALYTICS_CORE_METRICS, [100.5, 3])

    parsed = parse_ozon_analytics_page(response, OZON_ANALYTICS_CORE_METRICS)

    row = parsed["rows"][(1938260971, date(2026, 8, 23))]
    assert row["metrics"] == {"revenue": 100.5, "ordered_units": 3}
    assert parsed["totals"] == {"revenue": 100.5, "ordered_units": 3}
    assert "hits_view_search" not in row["metrics"]


@pytest.mark.asyncio
async def test_sync_analytics_merges_groups_by_sku_and_day_atomically():
    key = (1938260971, date(2026, 8, 23))
    core = {
        "rows": {
            key: {
                "sku": key[0],
                "sku_name": "Product",
                "stat_date": key[1],
                "metrics": {"revenue": 4474.8354, "ordered_units": 6},
                "row_data": {"metrics": [4474.8354, 6]},
                "api_timestamp": datetime(2026, 8, 24, 7, 5),
            }
        },
        "totals": {"revenue": 4474.8354, "ordered_units": 6},
        "raw_totals": [4474.8354, 6],
        "api_timestamp": datetime(2026, 8, 24, 7, 5),
        "page_count": 1,
    }
    outcome = {
        "rows": {
            key: {
                "sku": key[0],
                "sku_name": "Product",
                "stat_date": key[1],
                "metrics": {"returns": 1, "delivered_units": 5},
                "row_data": {"metrics": [1, 0, 5, 10]},
                "api_timestamp": datetime(2026, 8, 24, 7, 6),
            }
        },
        "totals": {"returns": 1, "delivered_units": 5},
        "raw_totals": [1, 0, 5, 10],
        "api_timestamp": datetime(2026, 8, 24, 7, 6),
        "page_count": 1,
    }
    service = object.__new__(OzonSyncService)
    service.db = AsyncMock()
    service.shop = SimpleNamespace(id=7)
    service.client = OzonClient("client-id", "api-key")
    service._fetch_analytics_metric_group = AsyncMock(side_effect=[core, outcome])
    service.sync_sales_funnel_dwd = AsyncMock(
        return_value={"status": "success", "count": 1}
    )

    with (
        patch(
            "kunpeng.services.ozon_sync_service."
            "crud_ods_ozon_analytics_data_daily.upsert_many",
            new=AsyncMock(return_value=[object()]),
        ) as upsert_rows,
        patch(
            "kunpeng.services.ozon_sync_service."
            "crud_ods_ozon_analytics_totals_window.upsert",
            new=AsyncMock(return_value=object()),
        ) as upsert_totals,
    ):
        result = await service.sync_analytics_data("2026-08-17", "2026-08-23")

    assert result["status"] == "success"
    item = upsert_rows.await_args.kwargs["items"][0]
    assert item["metrics"] == {
        "revenue": 4474.8354,
        "ordered_units": 6,
        "returns": 1,
        "delivered_units": 5,
    }
    assert item["has_core_metrics"] is True
    assert item["has_outcome_metrics"] is True
    upsert_totals.assert_awaited_once()
    service.db.commit.assert_awaited_once()
    service.db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_analytics_keeps_core_when_outcome_metrics_are_unsupported():
    key = (1938260971, date(2026, 8, 23))
    core = {
        "rows": {
            key: {
                "sku": key[0],
                "sku_name": "Product",
                "stat_date": key[1],
                "metrics": {"revenue": 100.5, "ordered_units": 3},
                "row_data": {"metrics": [100.5, 3]},
                "api_timestamp": None,
            }
        },
        "totals": {"revenue": 100.5, "ordered_units": 3},
        "raw_totals": [100.5, 3],
        "api_timestamp": None,
        "page_count": 1,
    }
    request = httpx.Request("POST", "https://api-seller.ozon.ru/v1/analytics/data")
    response = httpx.Response(
        400,
        request=request,
        json={"code": 3, "message": "deprecated metrics used"},
    )
    unsupported = httpx.HTTPStatusError(
        "bad request", request=request, response=response
    )
    service = object.__new__(OzonSyncService)
    service.db = AsyncMock()
    service.shop = SimpleNamespace(id=6)
    service.client = OzonClient("client-id", "api-key")
    service._fetch_analytics_metric_group = AsyncMock(
        side_effect=[core, unsupported]
    )
    service.sync_sales_funnel_dwd = AsyncMock(
        return_value={"status": "success", "count": 1}
    )

    with (
        patch(
            "kunpeng.services.ozon_sync_service."
            "crud_ods_ozon_analytics_data_daily.upsert_many",
            new=AsyncMock(return_value=[object()]),
        ) as upsert_rows,
        patch(
            "kunpeng.services.ozon_sync_service."
            "crud_ods_ozon_analytics_totals_window.upsert",
            new=AsyncMock(return_value=object()),
        ),
    ):
        result = await service.sync_analytics_data("2026-08-17", "2026-08-23")

    assert result["status"] == "success"
    assert result["outcome_pages"] == 0
    assert result["outcome_metrics_unavailable"] is True
    item = upsert_rows.await_args.kwargs["items"][0]
    assert item["metrics"] == {"revenue": 100.5, "ordered_units": 3}
    assert item["has_core_metrics"] is True
    assert item["has_outcome_metrics"] is False
    service.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_analytics_metric_group_uses_offset_pagination():
    service = object.__new__(OzonSyncService)
    service.client = SimpleNamespace(
        analytics=SimpleNamespace(get_analytics_data=AsyncMock(side_effect=[{}, {}]))
    )
    first = {
        "rows": {(1, date(2026, 8, 23)): {"sku": 1}},
        "totals": {"revenue": 1},
        "raw_totals": [1],
        "api_timestamp": None,
        "row_count": 1000,
    }
    second = {
        "rows": {(2, date(2026, 8, 23)): {"sku": 2}},
        "totals": {"revenue": 1},
        "raw_totals": [1],
        "api_timestamp": None,
        "row_count": 1,
    }

    with patch(
        "kunpeng.services.ozon_sync_service.parse_ozon_analytics_page",
        side_effect=[first, second],
    ):
        result = await service._fetch_analytics_metric_group(
            date_from="2026-08-23",
            date_to="2026-08-23",
            metrics=["revenue"],
            sort_key="revenue",
        )

    calls = service.client.analytics.get_analytics_data.await_args_list
    assert [call.kwargs["offset"] for call in calls] == [0, 1000]
    assert result["page_count"] == 2
    assert set(result["rows"]) == set(first["rows"]) | set(second["rows"])
