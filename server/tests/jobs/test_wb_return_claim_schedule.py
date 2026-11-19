from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_return_claim_job_runs_immediately_then_every_hour():
    now = datetime(2026, 7, 23, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(sync_wildberries.settings, "jobs_enabled", True),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job") as add_interval,
        patch.object(sync_wildberries.scheduler, "add_cron_job"),
    ):
        sync_wildberries.register_wildberries_jobs()

    claim_job = next(
        call
        for call in add_interval.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_return_claims_hourly"
    )
    assert claim_job.args[0] is sync_wildberries.sync_all_shops_return_claims
    assert claim_job.kwargs["minutes"] == 60
    assert claim_job.kwargs["next_run_time"] == now
