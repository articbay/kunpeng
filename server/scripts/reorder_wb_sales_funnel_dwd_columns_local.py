"""仅在本地数据库调整销售漏斗 DWD 的日期列顺序。"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kunpeng.config import settings  # noqa: E402

TABLE_NAME = "dwd_wb_sales_funnel_detail"


async def run() -> None:
    database_url = make_url(settings.database_url)
    if database_url.get_backend_name() != "mysql":
        raise RuntimeError("该脚本仅用于本地 MySQL 数据库")

    local_url = database_url.set(host="localhost")
    engine = create_async_engine(local_url, echo=False)

    try:
        async with engine.begin() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :database_name
                      AND table_name = :table_name
                    ORDER BY ordinal_position
                    """
                ),
                {
                    "database_name": local_url.database,
                    "table_name": TABLE_NAME,
                },
            )
            before = list(result.scalars())
            if not before:
                raise RuntimeError(f"本地表 {TABLE_NAME} 不存在")

            await connection.exec_driver_sql(
                """
                ALTER TABLE dwd_wb_sales_funnel_detail
                MODIFY COLUMN date_from DATE NOT NULL COMMENT '统计开始日期'
                AFTER shop_id
                """
            )
            await connection.exec_driver_sql(
                """
                ALTER TABLE dwd_wb_sales_funnel_detail
                MODIFY COLUMN date_to DATE NOT NULL COMMENT '统计结束日期（技术字段）'
                AFTER date_from
                """
            )

            result = await connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :database_name
                      AND table_name = :table_name
                    ORDER BY ordinal_position
                    """
                ),
                {
                    "database_name": local_url.database,
                    "table_name": TABLE_NAME,
                },
            )
            after = list(result.scalars())
            row_count = await connection.scalar(
                text("SELECT COUNT(*) FROM dwd_wb_sales_funnel_detail")
            )
    finally:
        await engine.dispose()

    print(f"BEFORE_FIRST_8={','.join(before[:8])}")
    print(f"AFTER_FIRST_8={','.join(after[:8])}")
    print(f"ROW_COUNT={row_count}")


if __name__ == "__main__":
    asyncio.run(run())
