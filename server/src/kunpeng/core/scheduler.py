import logging
from functools import wraps
from inspect import isawaitable
from typing import Any, Callable, Dict, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from kunpeng.config import settings

logger = logging.getLogger(__name__)

HOURLY_MISFIRE_GRACE_SECONDS = 2 * 60 * 60
DAILY_MISFIRE_GRACE_SECONDS = 12 * 60 * 60


class ScheduledJobBusinessError(RuntimeError):
    """Raised when a scheduled function returned an explicit business failure."""


def _contains_business_failure(result: Any) -> bool:
    """Inspect a job result without logging its potentially sensitive payload."""
    if not isinstance(result, dict):
        return False

    status = str(result.get("status", "")).strip().lower()
    if status.startswith(("error", "fail", "partial")):
        return True
    if result.get("failed_campaigns"):
        return True

    shop_results = result.get("results")
    if isinstance(shop_results, dict):
        return any(_contains_business_failure(value) for value in shop_results.values())
    return False


def _checked_job(func: Callable, func_kwargs: Dict[str, Any]) -> Callable:
    """Wrap scheduled calls so APScheduler sees returned business errors as failures."""

    @wraps(func)
    async def run_checked() -> Any:
        result = func(**func_kwargs)
        if isawaitable(result):
            result = await result
        if _contains_business_failure(result):
            raise ScheduledJobBusinessError(
                f"{func.__name__} completed with a business failure; see preceding task logs"
            )
        return result

    return run_checked


class TaskScheduler:
    """任务调度器封装"""

    def __init__(self):
        # 显式绑定平台业务时区(默认莫斯科)，使 cron/interval 的触发时刻与
        # 平台数据时区一致，且与宿主机 OS 时区解耦。
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.platform_timezone))
        self._running = False

    def add_job(
        self,
        func: Callable,
        trigger: Any = "interval",
        *,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        misfire_grace_time: int = 30,
        coalesce: bool = True,
        max_instances: int = 1,
        **trigger_args: Any,
    ) -> str:
        """
        添加定时任务

        Args:
            func: 要执行的函数
            trigger: 触发器类型 ('interval', 'cron', 'date') 或触发器对象
            job_id: 任务ID，默认自动生成
            name: 任务名称
            func_kwargs: 传递给任务函数的参数
            **trigger_args: 触发器参数

        Returns:
            任务ID
        """
        if job_id and job_id in settings.disabled_scheduled_job_ids:
            logger.info(
                "Skipped disabled job: %s - %s",
                job_id,
                name or func.__name__,
            )
            return job_id

        checked_func = _checked_job(func, func_kwargs or {})
        job = self.scheduler.add_job(
            checked_func,
            trigger=trigger,
            id=job_id,
            name=name,
            misfire_grace_time=misfire_grace_time,
            coalesce=coalesce,
            max_instances=max_instances,
            **trigger_args,
        )
        logger.info(f"Added job: {job.id} - {name or func.__name__}")
        return job.id

    def add_interval_job(
        self,
        func: Callable,
        *,
        minutes: int = 60,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """添加间隔执行任务"""
        kwargs.setdefault("misfire_grace_time", HOURLY_MISFIRE_GRACE_SECONDS)
        return self.add_job(
            func,
            trigger="interval",
            job_id=job_id,
            name=name,
            func_kwargs=func_kwargs,
            minutes=minutes,
            **kwargs,
        )

    def add_cron_job(
        self,
        func: Callable,
        *,
        cron: str,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        添加Cron任务

        Args:
            cron: Cron表达式，如 "0 0 * * *" (每天0点)
        """
        parts = cron.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron}")

        kwargs.setdefault("misfire_grace_time", DAILY_MISFIRE_GRACE_SECONDS)
        return self.add_job(
            func,
            trigger="cron",
            job_id=job_id,
            name=name,
            func_kwargs=func_kwargs,
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            **kwargs,
        )

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def start(self) -> None:
        """启动调度器"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器"""
        if self._running:
            self.scheduler.shutdown(wait=wait)
            self._running = False
            logger.info("Scheduler shut down")

    def get_jobs(self) -> list:
        """获取所有任务列表"""
        return self.scheduler.get_jobs()


# 全局调度器实例
scheduler = TaskScheduler()
