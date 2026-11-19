from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from kunpeng.jobs import sync_wildberries


def test_wb_order_dwd_reconcile_runs_immediately_then_daily():
    now = datetime(2026, 7, 31, 11, 0, tzinfo=ZoneInfo("Europe/Moscow"))

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
        if call.kwargs.get("job_id") == "wb_reconcile_order_dwd_daily"
    )
    assert dwd_job.args[0] is sync_wildberries.reconcile_wb_order_dwd
    assert dwd_job.kwargs["cron"] == "45 3 * * *"
    assert dwd_job.kwargs["next_run_time"] == now + timedelta(minutes=36)


def test_wb_dwd_chinese_translation_runs_immediately_every_15_minutes():
    now = datetime(2026, 8, 3, 16, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    with (
        patch.object(sync_wildberries.settings, "jobs_enabled", True),
        patch.object(sync_wildberries, "now_platform", return_value=now),
        patch.object(sync_wildberries.scheduler, "add_interval_job") as add_interval,
        patch.object(sync_wildberries.scheduler, "add_cron_job"),
    ):
        sync_wildberries.register_wildberries_jobs()

    translation_job = next(
        call
        for call in add_interval.call_args_list
        if call.kwargs.get("job_id") == "wb_translate_dwd_cn_every_15_minutes"
    )
    assert translation_job.args[0] is sync_wildberries.translate_wb_dwd_to_chinese
    assert translation_job.kwargs["minutes"] == 15
    assert translation_job.kwargs["next_run_time"] == now + timedelta(minutes=4)
