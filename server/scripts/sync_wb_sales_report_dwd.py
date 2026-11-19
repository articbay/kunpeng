"""手动构建 Wildberries 财务结算明细 DWD 表。"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kunpeng.core.database import AsyncSessionLocal  # noqa: E402
from kunpeng.services.wb_dwd_service import wb_dwd_service  # noqa: E402


async def run(batch_size: int) -> dict[str, int]:
    """执行一次全量、幂等的 ODS 到 DWD 同步。"""
    async with AsyncSessionLocal() as db:
        return await wb_dwd_service.sync_sales_report_detail(
            db,
            batch_size=batch_size,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 ods_wb_sales_reports 构建 DWD 财务结算明细",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="每批读取的 ODS 行数，默认 500",
    )
    args = parser.parse_args()
    stats = asyncio.run(run(args.batch_size))
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
