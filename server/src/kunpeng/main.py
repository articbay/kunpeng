from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import kunpeng.models  # noqa: F401  注册所有 SQLAlchemy 模型
from kunpeng.api.error_handlers import register_exception_handlers
from kunpeng.api.v1 import api_router
from kunpeng.config import settings
from kunpeng.core.database import engine
from kunpeng.core.logging import configure_logging
from kunpeng.core.middleware import LoggingMiddleware
from kunpeng.core.scheduler import scheduler
from kunpeng.jobs import register_ozon_jobs, register_wildberries_jobs
from kunpeng.models.base import Base

# 配置日志
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    # 表结构统一由 Alembic 迁移管理。生产环境禁用 create_all，避免与迁移版本产生漂移；
    # 仅在非生产环境为方便本地初始化时自动建表。
    if settings.environment != "production" and settings.auto_create_tables:
        logger.info("Initializing database tables (non-production)...")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables", error=str(e))
    elif settings.environment != "production":
        logger.info(
            "auto_create_tables=False，跳过非生产环境自动建表"
        )
    else:
        logger.info(
            "Production environment detected, skip create_all; schema managed by Alembic"
        )

    # 调度器仅在开启 run_scheduler 的进程中启动。生产采用“API 多 worker +
    # 独立单进程调度容器”，避免每个 uvicorn worker 各起一个 APScheduler 导致
    # 同一任务被并发触发多次（进而把外部平台接口打到限流 429）。
    if settings.run_scheduler:
        logger.info("Starting scheduler...")
        scheduler.start()

        # 注册定时任务
        logger.info("Registering scheduled jobs...")
        register_wildberries_jobs()
        register_ozon_jobs()
    else:
        logger.info("run_scheduler=False，本进程不启动调度器（仅提供 HTTP 服务）")

    yield
    # 关闭时
    if settings.run_scheduler:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


app = FastAPI(
    title=settings.app_name,
    description="跨境电商数据采集和分析系统",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 注册异常处理器
register_exception_handlers(app)

# 中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {"message": settings.app_name, "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
