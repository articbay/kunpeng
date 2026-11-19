from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_wb_lifecycle_dwm_runs_hourly_after_upstream_syncs() -> None:
    now = datetime(2026, 9, 1, 7, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    with (
        patch.object(sync_wildberries.settings, "environment", "production"),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job") as add_interval,
        patch.object(sync_wildberries.scheduler, "add_cron_job"),
    ):
        sync_wildberries.register_wildberries_jobs()

    jobs = {call.kwargs["job_id"]: call for call in add_interval.call_args_list}
    refresh_job = jobs["wb_refresh_order_lifecycle_dwm_hourly"]
    assert refresh_job.args[0] is sync_wildberries.refresh_wb_order_lifecycle_dwm
    assert refresh_job.kwargs["minutes"] == 60
    assert refresh_job.kwargs["next_run_time"] == now + timedelta(minutes=20)
