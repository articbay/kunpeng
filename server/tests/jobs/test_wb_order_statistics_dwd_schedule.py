from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_wb_order_statistics_dwd_reconcile_runs_immediately_then_daily():
    now = datetime(2026, 7, 31, 16, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(sync_wildberries.settings, "jobs_enabled", True),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job"),
        patch.object(sync_wildberries.scheduler, "add_cron_job") as add_cron,
    ):
        sync_wildberries.register_wildberries_jobs()

    dwd_job = next(
        call
        for call in add_cron.call_args_list
        if call.kwargs.get("job_id") == "wb_reconcile_order_statistics_dwd_daily"
    )
    assert dwd_job.args[0] is sync_wildberries.reconcile_wb_order_statistics_dwd
    assert dwd_job.kwargs["cron"] == "50 3 * * *"
    assert dwd_job.kwargs["next_run_time"] == now + timedelta(minutes=38)
