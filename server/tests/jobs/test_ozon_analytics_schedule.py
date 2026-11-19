from unittest.mock import patch

from kunpeng.jobs import sync_ozon


def test_ozon_analytics_runs_daily_at_seven_moscow_time():
    with (
        patch.object(sync_ozon.settings, "environment", "production"),
        patch.object(sync_ozon.scheduler, "add_interval_job"),
        patch.object(sync_ozon.scheduler, "add_cron_job") as add_cron,
    ):
        sync_ozon.register_ozon_jobs()

    jobs = {call.kwargs["job_id"]: call for call in add_cron.call_args_list}
    analytics_job = jobs["ozon_sync_analytics_data_daily"]
    assert analytics_job.args[0] is sync_ozon.sync_all_shops_analytics_data
    assert analytics_job.kwargs["cron"] == "0 7 * * *"
