import asyncio
import calendar
import sys
from datetime import date, timedelta

from sqlalchemy import select

from kunpeng.core.database import AsyncSessionLocal
from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


SHOP_ID = 8


def two_calendar_months_ago(today: date) -> date:
    month = today.month - 2
    year = today.year
    if month <= 0:
        month += 12
        year -= 1

    return date(
        year,
        month,
        min(today.day, calendar.monthrange(year, month)[1]),
    )


def split_into_31_day_windows(start_date: date, end_date: date):
    current_start = start_date
    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=30), end_date)
        yield current_start, current_end
        current_start = current_end + timedelta(days=1)


async def run_sync(name, operation, failures: list[str]) -> None:
    try:
        result = await operation()
        status = result.get("status", "unknown")
        count = result.get("count", 0)
        print(f"{name}: {status}，处理 {count} 条")

        if status not in {"success", "partial_success"}:
            failures.append(f"{name}: {result.get('message', '未知错误')}")
    except Exception as error:
        failures.append(f"{name}: {error}")
        print(f"{name}: 失败，{error}")


async def main() -> None:
    end_date = date.today() - timedelta(days=1)
    start_date = two_calendar_months_ago(date.today())
    start_datetime = f"{start_date.isoformat()}T00:00:00"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.id == SHOP_ID))
        shop = result.scalar_one_or_none()

        if shop is None:
            raise RuntimeError(f"测试库中不存在店铺 {SHOP_ID}")
        if shop.platform != "wildberries":
            raise RuntimeError(f"店铺 {SHOP_ID} 不是 Wildberries 店铺")

        service = WBSyncService(db, shop)
        failures: list[str] = []

        print(
            f"开始同步店铺 {SHOP_ID}："
            f"{start_date.isoformat()} 至 {end_date.isoformat()}"
        )

        await run_sync(
            "供应商订单及订单统计 DWD",
            lambda: service.sync_orders(start_datetime, None),
            failures,
        )
        await run_sync(
            "FBS 订单及订单明细 DWD",
            lambda: service.sync_marketplace_orders(
                start_datetime,
                f"{end_date.isoformat()}T23:59:59",
            ),
            failures,
        )
        await run_sync(
            "退货 DWD",
            lambda: service.sync_returns(
                start_date.isoformat(),
                end_date.isoformat(),
            ),
            failures,
        )
        await run_sync(
            "评价 DWD",
            lambda: service.sync_feedbacks(
                start_date.isoformat(),
                end_date.isoformat(),
            ),
            failures,
        )
        await run_sync(
            "提问 DWD",
            lambda: service.sync_questions(
                start_date.isoformat(),
                end_date.isoformat(),
            ),
            failures,
        )
        await run_sync(
            "财务报告周汇总 DWD",
            lambda: service.sync_sales_report_list(
                start_date.isoformat(),
                end_date.isoformat(),
            ),
            failures,
        )

        for window_start, window_end in split_into_31_day_windows(
            start_date,
            end_date,
        ):
            label = f"{window_start.isoformat()} 至 {window_end.isoformat()}"

            await run_sync(
                f"财务结算明细 DWD（{label}）",
                lambda start=window_start, end=window_end: service.sync_finance(
                    start.isoformat(),
                    end.isoformat(),
                ),
                failures,
            )

        current_date = start_date
        while current_date <= end_date:
            date_text = current_date.isoformat()

            await run_sync(
                f"销售漏斗 DWD（{date_text}）",
                lambda value=date_text: service.sync_funnel(value, value),
                failures,
            )
            await run_sync(
                f"广告 ODS（{date_text}）",
                lambda value=date_text: service.sync_adverts(value, value),
                failures,
            )

            current_date += timedelta(days=1)

        if failures:
            print("\n以下同步未完成：")
            for failure in failures:
                print(f"- {failure}")
            sys.exit(1)

        print("\n全部同步完成。")


if __name__ == "__main__":
    asyncio.run(main())