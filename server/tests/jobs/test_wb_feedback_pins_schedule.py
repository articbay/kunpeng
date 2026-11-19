from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_feedback_pins_job_runs_immediately_then_daily_at_three():
    now = datetime(2026, 7, 26, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(sync_wildberries.settings, "jobs_enabled", True),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job"),
        patch.object(sync_wildberries.scheduler, "add_cron_job") as add_cron,
    ):
        sync_wildberries.register_wildberries_jobs()

    feedback_pins_job = next(
        call
        for call in add_cron.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_feedback_pins_daily"
    )
    assert feedback_pins_job.args[0] is sync_wildberries.sync_all_shops_feedback_pins
    assert feedback_pins_job.kwargs["cron"] == "0 3 * * *"
    assert feedback_pins_job.kwargs["next_run_time"] == now + timedelta(minutes=20)
