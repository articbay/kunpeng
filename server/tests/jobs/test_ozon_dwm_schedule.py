from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_ozon


def test_ozon_dwm_refresh_runs_hourly_after_upstream_syncs() -> None:
    now = datetime(2026, 8, 7, 7, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    with (
        patch.object(sync_ozon.settings, "environment", "production"),
        patch.object(sync_ozon, "now_platform", return_value=now),
        patch.object(sync_ozon.scheduler, "add_interval_job") as add_interval,
        patch.object(sync_ozon.scheduler, "add_cron_job"),
    ):
        sync_ozon.register_ozon_jobs()

    jobs = {call.kwargs["job_id"]: call for call in add_interval.call_args_list}
    refresh_job = jobs["ozon_refresh_dwm_hourly"]
    assert refresh_job.args[0] is sync_ozon.refresh_ozon_dwm_tables
    assert refresh_job.kwargs["minutes"] == 60
    assert refresh_job.kwargs["next_run_time"] == now + timedelta(minutes=15)
