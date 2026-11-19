"""手动同步 localhost 的 WB 财务报告列表 ODS 和 DWD。"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kunpeng.config import settings  # noqa: E402
from kunpeng.models.shop import Shop  # noqa: E402
from kunpeng.services.wb_sync_service import WBSyncService  # noqa: E402

LOCAL_HOST = "localhost"


def build_local_database_url(database_url: str) -> URL:
    """保留数据库配置，但强制连接 localhost。"""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return url
    return url.set(host=LOCAL_HOST)


async def run(shop_id: int, date_from: str, date_to: str) -> dict:
    """同步指定店铺和日期范围，ODS 成功后由 Service 自动同步 DWD。"""
    start_date = date.fromisoformat(date_from)
    end_date = date.fromisoformat(date_to)
    if start_date > end_date:
        raise ValueError("date_from 不能晚于 date_to")

    local_url = build_local_database_url(settings.database_url)
    engine = create_async_engine(
        local_url,
        echo=False,
        connect_args=(
            {"check_same_thread": False}
            if local_url.get_backend_name() == "sqlite"
            else {}
        ),
    )
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    try:
        async with session_factory() as db:
            shop = await db.get(Shop, shop_id)
            if shop is None:
                raise ValueError(f"店铺 {shop_id} 不存在")
            if shop.platform != "wildberries":
                raise ValueError(f"店铺 {shop_id} 不是 Wildberries 店铺")

            return await WBSyncService(db, shop).sync_sales_report_list(
                date_from,
                date_to,
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步 localhost 的 WB 财务报告列表到 ODS 和 DWD",
    )
    parser.add_argument("--shop-id", type=int, required=True)
    parser.add_argument("--date-from", required=True, help="YYYY-MM-DD")
    parser.add_argument("--date-to", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    result = asyncio.run(run(args.shop_id, args.date_from, args.date_to))
    print(json.dumps(result, ensure_ascii=False, default=str))
    if result.get("status") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
