"""
集成测试专用 fixture

解决 SQLAlchemy async engine 连接池跨 event loop 的问题：
pytest-asyncio 默认为每个测试创建新的 event loop，而全局 engine 的
连接池会缓存上一个 loop 的连接，复用时报 "attached to a different loop"。

通过在每个测试前后 dispose engine，强制每个测试使用全新的连接池。
"""

import pytest_asyncio

from kunpeng.core.database import engine


@pytest_asyncio.fixture(autouse=True)
async def reset_engine_pool():
    """每个测试前后释放数据库连接池，避免跨 event loop 复用连接"""
    await engine.dispose()
    yield
    await engine.dispose()
