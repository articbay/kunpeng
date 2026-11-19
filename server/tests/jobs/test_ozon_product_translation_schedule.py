from unittest.mock import patch

from kunpeng.jobs import sync_ozon


def test_product_translation_runs_daily_after_product_sync():
    with (
        patch.object(sync_ozon.settings, "environment", "production"),
        patch.object(sync_ozon.scheduler, "add_interval_job"),
        patch.object(sync_ozon.scheduler, "add_cron_job") as add_cron,
    ):
        sync_ozon.register_ozon_jobs()

    jobs = {call.kwargs["job_id"]: call for call in add_cron.call_args_list}
    product_job = jobs["ozon_sync_products_daily"]
    translation_job = jobs["ozon_translate_product_names_daily"]

    assert product_job.kwargs["cron"] == "30 4 * * *"
    assert translation_job.args[0] is sync_ozon.translate_ozon_product_names
    assert translation_job.kwargs["cron"] == "45 4 * * *"
