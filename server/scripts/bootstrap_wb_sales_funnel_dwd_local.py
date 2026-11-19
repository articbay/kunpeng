"""仅在本地数据库直建并同步 Wildberries 销售漏斗 DWD 表。"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kunpeng.config import settings  # noqa: E402
from kunpeng.models.dwd.wildberries.funnel import DWDWBSalesFunnelDetail  # noqa: E402
from kunpeng.services.wb_dwd_service import wb_dwd_service  # noqa: E402

LOCAL_HOST = "localhost"


def build_local_database_url(database_url: str) -> URL:
    """保留账号、端口和库名，但强制数据库主机为 localhost。"""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return url
    return url.set(host=LOCAL_HOST)


async def run(batch_size: int) -> dict[str, int | bool]:
    """直建目标表，然后执行一次全量、幂等同步。"""
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    local_url = build_local_database_url(settings.database_url)
    local_engine = create_async_engine(
        local_url,
        echo=False,
        connect_args=(
            {"check_same_thread": False}
            if local_url.get_backend_name() == "sqlite"
            else {}
        ),
    )
    session_factory = async_sessionmaker(
        local_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    try:
        async with local_engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: DWDWBSalesFunnelDetail.__table__.create(
                    sync_connection,
                    checkfirst=True,
                )
            )

        async with session_factory() as db:
            stats = await wb_dwd_service.sync_sales_funnel_detail(
                db,
                batch_size=batch_size,
            )
        return {"table_created_or_exists": True, **stats}
    finally:
        await local_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("仅连接 localhost，直建 dwd_wb_sales_funnel_detail 后同步 ODS"),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="每批读取的 ODS 行数，默认 500",
    )
    args = parser.parse_args()
    result = asyncio.run(run(args.batch_size))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
