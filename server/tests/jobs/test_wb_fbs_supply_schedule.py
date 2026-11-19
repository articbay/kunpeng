from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_fbs_supply_job_runs_immediately_then_daily_at_three():
    now = datetime(2026, 7, 24, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(sync_wildberries.settings, "jobs_enabled", True),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job"),
        patch.object(sync_wildberries.scheduler, "add_cron_job") as add_cron,
    ):
        sync_wildberries.register_wildberries_jobs()

    supply_job = next(
        call
        for call in add_cron.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_fbs_supplies_daily"
    )
    assert supply_job.args[0] is sync_wildberries.sync_all_shops_fbs_supplies
    assert supply_job.kwargs["cron"] == "10 3 * * *"
    assert supply_job.kwargs["next_run_time"] == now + timedelta(minutes=24)
