"""Wildberries 定时任务注册测试。"""

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from kunpeng.config import settings
from kunpeng.jobs import sync_wildberries


def test_region_sales_window_uses_two_completed_platform_days(monkeypatch):
    monkeypatch.setattr(
        sync_wildberries,
        "now_platform",
        lambda: datetime(2026, 7, 24, 3, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    assert sync_wildberries._get_region_sales_date_window(2) == (
        "2026-07-22",
        "2026-07-23",
    )
    assert sync_wildberries._get_product_search_texts_date_window(2) == (
        "2026-07-22",
        "2026-07-23",
    )
    assert sync_wildberries._get_search_traffic_date_window(7) == (
        "2026-07-17",
        "2026-07-23",
    )


def test_sales_report_list_window_uses_previous_calendar_week(monkeypatch):
    monkeypatch.setattr(
        sync_wildberries,
        "now_platform",
        lambda: datetime(2026, 7, 29, 3, 5, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    assert sync_wildberries._get_previous_week_date_window() == (
        "2026-07-20",
        "2026-07-26",
    )


def test_registers_seller_balance_daily_at_three(monkeypatch):
    add_cron_job = Mock()
    monkeypatch.setattr(sync_wildberries.scheduler, "add_cron_job", add_cron_job)
    monkeypatch.setattr(sync_wildberries.scheduler, "add_interval_job", Mock())
    monkeypatch.setattr(settings, "jobs_enabled", True)

    sync_wildberries.register_wildberries_jobs()

    matching_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_seller_balance_daily"
    ]
    assert len(matching_calls) == 1
    assert matching_calls[0].args[0] is sync_wildberries.sync_all_shops_seller_balance
    assert matching_calls[0].kwargs["cron"] == "0 3 * * *"

    report_list_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_sales_report_list_weekly"
    ]
    assert len(report_list_calls) == 1
    assert (
        report_list_calls[0].args[0]
        is sync_wildberries.sync_all_shops_sales_report_list
    )
    assert report_list_calls[0].kwargs["cron"] == "5 3 * * mon"

    region_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_region_sales_daily"
    ]
    assert len(region_calls) == 1
    assert region_calls[0].args[0] is sync_wildberries.sync_all_shops_region_sales
    assert region_calls[0].kwargs["cron"] == "5 3 * * *"

    search_traffic_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_search_traffic_daily"
    ]
    assert len(search_traffic_calls) == 1
    assert (
        search_traffic_calls[0].args[0]
        is sync_wildberries.sync_all_shops_search_traffic
    )
    assert search_traffic_calls[0].kwargs["cron"] == "15 3 * * *"

    product_search_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_product_search_texts_daily"
    ]
    assert len(product_search_calls) == 1
    assert (
        product_search_calls[0].args[0]
        is sync_wildberries.sync_all_shops_product_search_texts
    )
    assert product_search_calls[0].kwargs["cron"] == "35 3 * * *"

    finance_daily_calls = [
        call
        for call in add_cron_job.call_args_list
        if call.kwargs.get("job_id") == "wb_sync_finance_daily_by_day"
    ]
    assert len(finance_daily_calls) == 1
    assert (
        finance_daily_calls[0].args[0] is sync_wildberries.sync_all_shops_finance_daily
    )
    assert finance_daily_calls[0].kwargs["cron"] == "0 10 * * *"
