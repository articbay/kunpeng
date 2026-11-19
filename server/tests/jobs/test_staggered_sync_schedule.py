from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_ozon, sync_wildberries


def _registered_interval_times(module, now):
    with (
        patch.object(module.settings, "environment", "production"),
        patch.object(module, "now_platform", return_value=now),
        patch.object(module.scheduler, "add_interval_job") as add_interval,
        patch.object(module.scheduler, "add_cron_job"),
    ):
        if module is sync_wildberries:
            module.register_wildberries_jobs()
        else:
            module.register_ozon_jobs()
    return {
        call.kwargs["job_id"]: call.kwargs.get("next_run_time")
        for call in add_interval.call_args_list
    }


def test_wb_hourly_startup_is_staggered() -> None:
    now = datetime(2026, 8, 7, 7, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    run_times = _registered_interval_times(sync_wildberries, now)

    assert run_times["wb_sync_return_claims_hourly"] == now
    assert run_times["wb_sync_chat_events_hourly"] == now + timedelta(minutes=2)
    assert run_times["wb_sync_sales_hourly"] == now + timedelta(minutes=6)
    assert run_times["wb_sync_new_orders_hourly"] == now + timedelta(minutes=18)
    assert len(set(run_times.values())) == len(run_times)


def test_ozon_hourly_startup_is_staggered_and_reviews_remain_enabled() -> None:
    now = datetime(2026, 8, 7, 7, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    run_times = _registered_interval_times(sync_ozon, now)

    assert run_times["ozon_sync_unfulfilled_postings_hourly"] == now + timedelta(
        minutes=1
    )
    assert run_times["ozon_sync_reviews_hourly"] == now + timedelta(minutes=9)
    assert len(set(run_times.values())) == len(run_times)
