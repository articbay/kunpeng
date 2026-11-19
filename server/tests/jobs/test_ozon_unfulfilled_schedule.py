from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_ozon


def test_unfulfilled_window_is_yesterday_midnight_to_actual_run_time():
    run_at = datetime(
        2026,
        7,
        27,
        10,
        17,
        43,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )

    with patch.object(
        sync_ozon.settings.sync,
        "ozon_unfulfilled_lookback_days",
        1,
    ):
        window_start, window_end = sync_ozon._unfulfilled_cutoff_window(run_at)

    assert window_start == datetime(
        2026,
        7,
        26,
        0,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )
    assert window_end == run_at


def test_unfulfilled_job_runs_on_start_then_every_hour():
    now = datetime(
        2026,
        7,
        27,
        10,
        0,
        tzinfo=ZoneInfo("Europe/Moscow"),
    )

    with (
        patch.object(sync_ozon.settings, "jobs_enabled", True),
        patch.object(sync_ozon, "now_platform", return_value=now),
        patch.object(sync_ozon.scheduler, "add_interval_job") as add_interval,
        patch.object(sync_ozon.scheduler, "add_cron_job"),
    ):
        sync_ozon.register_ozon_jobs()

    job = next(
        call
        for call in add_interval.call_args_list
        if call.kwargs.get("job_id") == "ozon_sync_unfulfilled_postings_hourly"
    )
    assert job.args[0] is sync_ozon.sync_all_shops_unfulfilled_postings
    assert job.kwargs["minutes"] == 60
    assert job.kwargs["next_run_time"] == now + timedelta(minutes=1)
