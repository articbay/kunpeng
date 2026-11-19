from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from kunpeng.services.ozon_sync_service import OzonSyncService


class FakeDb:
    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


class AsyncContextClient:
    def __init__(self):
        self.posting = SimpleNamespace()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def _service() -> OzonSyncService:
    shop = SimpleNamespace(
        id=7,
        platform_shop_id="client-id",
        api_key="api-key",
        performance_client_id=None,
        performance_client_secret=None,
    )
    service = OzonSyncService(FakeDb(), shop)
    service.client = AsyncContextClient()
    return service


def _window():
    moscow = ZoneInfo("Europe/Moscow")
    return (
        datetime(2026, 7, 26, 0, 0, tzinfo=moscow),
        datetime(2026, 7, 27, 10, 0, tzinfo=moscow),
    )


@pytest.mark.asyncio
async def test_v4_cursor_pages_are_fully_fetched_before_reconciliation():
    service = _service()
    window_start, window_end = _window()
    service.client.posting.get_unfulfilled_postings = AsyncMock(
        side_effect=[
            {
                "postings": [
                    {"posting_number": "P-1"},
                    {"posting_number": "P-2"},
                ],
                "count": 2,
                "cursor": "cursor-2",
                "has_next": True,
            },
            {
                "postings": [{"posting_number": "P-2"}],
                "count": 2,
                "cursor": "",
                "has_next": False,
            },
        ]
    )

    with patch(
        "kunpeng.services.ozon_sync_service." "crud_ods_ozon_unfulfilled_posting"
    ) as crud:
        crud.reconcile_snapshot = AsyncMock(
            return_value={
                "count": 2,
                "ods_count": 2,
                "new_count": 2,
                "reactivated_count": 0,
                "resolved_count": 0,
            }
        )
        result = await service.sync_unfulfilled_postings(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["scanned_count"] == 3
    assert result["page_count"] == 2
    assert service.db.commit_count == 1
    assert service.db.rollback_count == 0
    assert (
        service.client.posting.get_unfulfilled_postings.await_args_list[0].kwargs[
            "cursor"
        ]
        == ""
    )
    assert (
        service.client.posting.get_unfulfilled_postings.await_args_list[1].kwargs[
            "cursor"
        ]
        == "cursor-2"
    )
    first_call = service.client.posting.get_unfulfilled_postings.await_args_list[0]
    assert first_call.kwargs["cutoff_from"] == "2026-07-25T21:00:00.000Z"
    assert first_call.kwargs["cutoff_to"] == "2026-07-27T07:00:00.000Z"
    reconciled_items = crud.reconcile_snapshot.await_args.kwargs["items"]
    assert {item["posting_number"] for item in reconciled_items} == {
        "P-1",
        "P-2",
    }
    assert crud.reconcile_snapshot.await_args.kwargs["observed_at"] == datetime(
        2026, 7, 27, 7, 0
    )


@pytest.mark.asyncio
async def test_empty_complete_snapshot_is_reconciled():
    service = _service()
    window_start, window_end = _window()
    service.client.posting.get_unfulfilled_postings = AsyncMock(
        return_value={
            "postings": [],
            "count": 0,
            "cursor": "",
            "has_next": False,
        }
    )

    with patch(
        "kunpeng.services.ozon_sync_service." "crud_ods_ozon_unfulfilled_posting"
    ) as crud:
        crud.reconcile_snapshot = AsyncMock(
            return_value={
                "count": 0,
                "ods_count": 0,
                "new_count": 0,
                "reactivated_count": 0,
                "resolved_count": 1,
            }
        )
        result = await service.sync_unfulfilled_postings(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "success"
    assert result["resolved_count"] == 1
    crud.reconcile_snapshot.assert_awaited_once()
    assert service.db.commit_count == 1


@pytest.mark.asyncio
async def test_repeated_cursor_aborts_without_reconciliation():
    service = _service()
    window_start, window_end = _window()
    service.client.posting.get_unfulfilled_postings = AsyncMock(
        return_value={
            "postings": [{"posting_number": "P-1"}],
            "count": 1,
            "cursor": "",
            "has_next": True,
        }
    )

    with patch(
        "kunpeng.services.ozon_sync_service." "crud_ods_ozon_unfulfilled_posting"
    ) as crud:
        result = await service.sync_unfulfilled_postings(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "error"
    assert "游标" in result["message"]
    crud.reconcile_snapshot.assert_not_called()
    assert service.db.commit_count == 0
    assert service.db.rollback_count == 1


@pytest.mark.asyncio
async def test_second_page_failure_does_not_resolve_existing_rows():
    service = _service()
    window_start, window_end = _window()
    service.client.posting.get_unfulfilled_postings = AsyncMock(
        side_effect=[
            {
                "postings": [{"posting_number": "P-1"}],
                "count": 2,
                "cursor": "cursor-2",
                "has_next": True,
            },
            RuntimeError("temporary API failure"),
        ]
    )

    with patch(
        "kunpeng.services.ozon_sync_service." "crud_ods_ozon_unfulfilled_posting"
    ) as crud:
        result = await service.sync_unfulfilled_postings(
            window_start=window_start,
            window_end=window_end,
        )

    assert result["status"] == "error"
    crud.reconcile_snapshot.assert_not_called()
    assert service.db.commit_count == 0
    assert service.db.rollback_count == 1
