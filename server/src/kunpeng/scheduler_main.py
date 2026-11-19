"""独立调度进程入口

生产部署为“API 多 worker + 独立单进程调度器”：
- API 容器（uvicorn --workers N）设置 RUN_SCHEDULER=false，仅提供 HTTP，不注册调度；
- 本进程为唯一的调度来源，单进程运行 APScheduler，避免同一任务被并发触发多次
  而把外部平台接口打到限流(429)。

启动方式：
    python -m kunpeng.scheduler_main
"""

import asyncio
import logging
import signal

import kunpeng.models  # noqa: F401  注册所有 SQLAlchemy 模型
from kunpeng.core.logging import configure_logging
from kunpeng.core.scheduler import scheduler
from kunpeng.jobs import register_ozon_jobs, register_wildberries_jobs

configure_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    """启动调度器并常驻，收到终止信号后优雅关闭。"""
    logger.info("[调度进程] 启动调度器...")
    scheduler.start()

    logger.info("[调度进程] 注册定时任务...")
    register_wildberries_jobs()
    register_ozon_jobs()

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # 某些平台（如 Windows）不支持 add_signal_handler
            pass

    jobs = scheduler.get_jobs()
    logger.info(f"[调度进程] 已注册 {len(jobs)} 个任务，进入常驻等待")

    await stop_event.wait()

    logger.info("[调度进程] 收到终止信号，关闭调度器...")
    scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
