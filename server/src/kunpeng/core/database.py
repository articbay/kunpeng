from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from kunpeng.config import settings

# 创建异步引擎。MySQL 长驻调度进程会经历电脑休眠、网络抖动和服务重启，
# pre_ping/recycle 可避免从连接池中取到已经失效的旧连接。
engine_options: Dict[str, Any] = {"echo": settings.debug}
if "sqlite" in settings.database_url:
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update(
        {
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
        }
    )

engine = create_async_engine(settings.database_url, **engine_options)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 基类模型
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数

    用法:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
