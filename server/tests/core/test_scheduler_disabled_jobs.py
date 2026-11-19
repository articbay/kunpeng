import pytest

from kunpeng.config import settings
from kunpeng.core.scheduler import (
    DAILY_MISFIRE_GRACE_SECONDS,
    HOURLY_MISFIRE_GRACE_SECONDS,
    ScheduledJobBusinessError,
    TaskScheduler,
)


def _sample_job() -> None:
    pass


def test_disabled_job_is_not_registered(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "disabled_scheduled_jobs",
        "wb_sync_adverts_daily, wb_sync_search_cluster_stat_hourly",
    )
    task_scheduler = TaskScheduler()

    returned_job_id = task_scheduler.add_interval_job(
        _sample_job,
        job_id="wb_sync_adverts_daily",
    )

    assert returned_job_id == "wb_sync_adverts_daily"
    assert task_scheduler.get_jobs() == []


def test_job_not_in_blacklist_is_registered(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "disabled_scheduled_jobs",
        "wb_sync_adverts_daily",
    )
    task_scheduler = TaskScheduler()

    task_scheduler.add_interval_job(
        _sample_job,
        job_id="wb_sync_orders_hourly",
    )

    assert [job.id for job in task_scheduler.get_jobs()] == ["wb_sync_orders_hourly"]


def test_interval_and_cron_jobs_have_resume_grace(monkeypatch) -> None:
    monkeypatch.setattr(settings, "disabled_scheduled_jobs", "")
    task_scheduler = TaskScheduler()

    task_scheduler.add_interval_job(_sample_job, job_id="hourly")
    task_scheduler.add_cron_job(_sample_job, cron="0 3 * * *", job_id="daily")

    jobs = {job.id: job for job in task_scheduler.get_jobs()}
    assert jobs["hourly"].misfire_grace_time == HOURLY_MISFIRE_GRACE_SECONDS
    assert jobs["daily"].misfire_grace_time == DAILY_MISFIRE_GRACE_SECONDS
    assert jobs["hourly"].coalesce is True
    assert jobs["hourly"].max_instances == 1


@pytest.mark.asyncio
async def test_scheduled_business_error_is_exposed_to_apscheduler(monkeypatch) -> None:
    monkeypatch.setattr(settings, "disabled_scheduled_jobs", "")
    task_scheduler = TaskScheduler()

    async def failing_job():
        return {"status": "success", "results": {8: {"status": "error"}}}

    task_scheduler.add_interval_job(failing_job, job_id="failing")
    job = task_scheduler.get_jobs()[0]

    with pytest.raises(ScheduledJobBusinessError):
        await job.func()
