import argparse
import asyncio
import calendar
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.engine import make_url

from kunpeng.config import settings
from kunpeng.core.database import AsyncSessionLocal
from kunpeng.models.shop import Shop
from kunpeng.services.ozon_sync_service import OzonSyncService

ALLOWED_DATABASE = "kunpeng_test"


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("日期格式必须是 YYYY-MM-DD") from error


def two_calendar_months_ago(today: date) -> date:
    month_index = today.year * 12 + today.month - 1 - 2
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def iter_months(start_date: date, end_date: date):
    year = start_date.year
    month = start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        yield year, month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1


def build_parser() -> argparse.ArgumentParser:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="手动同步测试库中的 Ozon 评价和财务结算报告",
    )
    parser.add_argument("--shop-id", type=int, required=True, help="Ozon 店铺 ID")
    parser.add_argument(
        "--date-from",
        type=parse_date,
        default=two_calendar_months_ago(today),
        help="评价同步开始日期，默认近两个日历月，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--date-to",
        type=parse_date,
        default=today,
        help="评价同步结束日期，默认今天，格式 YYYY-MM-DD",
    )
    return parser


async def run_operation(name: str, operation, failures: list[str]) -> None:
    try:
        result = await operation()
    except Exception as error:
        failures.append(f"{name}: {error}")
        print(f"{name}: 失败，{error}")
        return

    status = result.get("status", "unknown")
    count = result.get("count", 0)
    print(f"{name}: {status}，处理 {count} 条")
    if status not in {"success", "partial_success"}:
        failures.append(f"{name}: {result.get('message', '未知错误')}")


async def main() -> int:
    args = build_parser().parse_args()
    if args.date_from > args.date_to:
        raise ValueError("--date-from 不能晚于 --date-to")

    database_name = make_url(settings.database_url).database
    if database_name != ALLOWED_DATABASE:
        raise RuntimeError(
            f"为防止误操作，脚本只允许连接 {ALLOWED_DATABASE}，"
            f"当前数据库为 {database_name}"
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.id == args.shop_id))
        shop = result.scalar_one_or_none()
        if shop is None:
            raise RuntimeError(f"测试库中不存在店铺 {args.shop_id}")
        if shop.platform != "ozon":
            raise RuntimeError(f"店铺 {args.shop_id} 不是 Ozon 店铺")

        service = OzonSyncService(db, shop)
        failures: list[str] = []
        print(
            f"开始同步 Ozon 店铺 {args.shop_id}："
            f"{args.date_from.isoformat()} 至 {args.date_to.isoformat()}"
        )

        await run_operation(
            "评价 ODS",
            lambda: service.sync_reviews(
                args.date_from.isoformat(),
                args.date_to.isoformat(),
            ),
            failures,
        )

        for year, month in iter_months(args.date_from, args.date_to):
            await run_operation(
                f"财务结算 ODS（{year}-{month:02d}）",
                lambda value_year=year, value_month=month: service.sync_realization_report(
                    year=value_year,
                    month=value_month,
                ),
                failures,
            )

        if failures:
            print("\n以下同步未完成：")
            for failure in failures:
                print(f"- {failure}")
            return 1

        print("\n评价和财务结算同步完成。")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
