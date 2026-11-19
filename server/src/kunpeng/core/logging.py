"""
日志配置模块
"""
import logging
import sys
from typing import Any
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog
from structlog.types import Processor

from kunpeng.config import settings


def configure_logging() -> None:
    """配置 structlog"""
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.debug:
        # 开发环境：彩色控制台输出
        processors = shared_processors + [
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # 生产环境：JSON 输出
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # 文件输出（带旋转）
    file_handler = RotatingFileHandler(
        log_dir / "kunpeng.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # 保留5个备份
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> Any:
    """获取 logger"""
    return structlog.get_logger(name)
