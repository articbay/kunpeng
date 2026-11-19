#!/usr/bin/env python
"""启动任务调度器"""

import asyncio
import sys

sys.path.insert(0, "src")

import logging
from kunpeng.core.scheduler import scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting scheduler...")
    scheduler.start()

    try:
        # 保持运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
