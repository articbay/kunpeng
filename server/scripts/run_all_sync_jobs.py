#!/usr/bin/env python
"""Run every registered platform sync job sequentially against configured storage.

This operational runner deliberately avoids starting APScheduler.  It is intended
for a one-off test-environment catch-up while the standalone scheduler is paused.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import kunpeng.models  # noqa: F401  Ensure all SQLAlchemy models are registered.
from kunpeng.jobs.sync_ozon import (
    sync_all_shops_accrual_types as ozon_accrual_types,
    sync_all_shops_advert_products as ozon_advert_products,
    sync_all_shops_advert_products_hourly as ozon_advert_products_hourly,
    sync_all_shops_adverts as ozon_adverts,
    sync_all_shops_fbo_postings as ozon_fbo_postings,
    sync_all_shops_finance as ozon_finance,
    sync_all_shops_postings as ozon_postings,
    sync_all_shops_products as ozon_products,
    sync_all_shops_returns as ozon_returns,
    sync_all_shops_reviews as ozon_reviews,
    sync_all_shops_unfulfilled_postings as ozon_unfulfilled_postings,
)
from kunpeng.jobs.sync_wildberries import (
    sync_all_shops_advert_stats_hourly as wb_advert_stats_hourly,
    sync_all_shops_adverts as wb_adverts,
    sync_all_shops_balance as wb_balance,
    sync_all_shops_feedbacks as wb_feedbacks,
    sync_all_shops_finance as wb_finance,
    sync_all_shops_funnel as wb_funnel,
    sync_all_shops_marketplace_orders as wb_marketplace_orders,
    sync_all_shops_new_orders as wb_new_orders,
    sync_all_shops_orders as wb_orders,
    sync_all_shops_questions as wb_questions,
    sync_all_shops_returns as wb_returns,
    sync_all_shops_sales as wb_sales,
    sync_all_shops_search_cluster_stat_hourly as wb_search_cluster_hourly,
)


Job = Callable[[], Awaitable[dict[str, Any]]]


JOBS: list[tuple[str, Job, float]] = [
    ("wb_balance", wb_balance, 3),
    ("wb_sales", wb_sales, 3),
    ("wb_orders", wb_orders, 3),
    ("wb_marketplace_orders", wb_marketplace_orders, 3),
    ("wb_new_orders", wb_new_orders, 3),
    ("wb_feedbacks", wb_feedbacks, 3),
    ("wb_questions", wb_questions, 3),
    ("wb_returns", wb_returns, 3),
    ("wb_finance", wb_finance, 3),
    ("wb_funnel", wb_funnel, 3),
    ("wb_adverts", wb_adverts, 25),
    ("wb_advert_stats_hourly", wb_advert_stats_hourly, 25),
    ("wb_search_cluster_hourly", wb_search_cluster_hourly, 25),
    ("ozon_accrual_types", ozon_accrual_types, 3),
    ("ozon_products", ozon_products, 3),
    ("ozon_postings", ozon_postings, 3),
    ("ozon_fbo_postings", ozon_fbo_postings, 3),
    ("ozon_unfulfilled_postings", ozon_unfulfilled_postings, 3),
    ("ozon_returns", ozon_returns, 3),
    ("ozon_reviews", ozon_reviews, 3),
    ("ozon_finance", ozon_finance, 3),
    ("ozon_adverts", ozon_adverts, 65),
    ("ozon_advert_products", ozon_advert_products, 65),
    ("ozon_advert_products_hourly", ozon_advert_products_hourly, 0),
]


def contains_error(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("status") == "error":
            return True
        return any(contains_error(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_error(item) for item in value)
    return False


async def run_job(name: str, job: Job, retries: int, retry_delay: float) -> dict[str, Any]:
    for attempt in range(1, retries + 2):
        print(f"FULL_SYNC_START name={name} attempt={attempt}", flush=True)
        try:
            result = await job()
        except Exception as exc:  # Continue so one platform failure does not hide later results.
            result = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

        failed = contains_error(result)
        print(
            "FULL_SYNC_RESULT "
            + json.dumps(
                {"name": name, "attempt": attempt, "failed": failed, "result": result},
                ensure_ascii=False,
                default=str,
            ),
            flush=True,
        )
        if not failed or attempt > retries:
            return {"failed": failed, "attempts": attempt, "result": result}

        print(f"FULL_SYNC_RETRY name={name} wait_seconds={retry_delay}", flush=True)
        await asyncio.sleep(retry_delay)

    raise RuntimeError("unreachable")


async def main() -> None:
    retries = int(os.getenv("FULL_SYNC_RETRIES", "1"))
    retry_delay = float(os.getenv("FULL_SYNC_RETRY_DELAY_SECONDS", "90"))
    summaries: dict[str, Any] = {}

    print(f"FULL_SYNC_BEGIN jobs={len(JOBS)} retries={retries}", flush=True)
    for index, (name, job, cooldown) in enumerate(JOBS, start=1):
        print(f"FULL_SYNC_PROGRESS index={index}/{len(JOBS)} name={name}", flush=True)
        summaries[name] = await run_job(name, job, retries, retry_delay)
        if cooldown:
            print(f"FULL_SYNC_COOLDOWN name={name} seconds={cooldown}", flush=True)
            await asyncio.sleep(cooldown)

    failed_jobs = [name for name, summary in summaries.items() if summary["failed"]]
    print(
        "FULL_SYNC_SUMMARY "
        + json.dumps(
            {
                "total": len(summaries),
                "succeeded": len(summaries) - len(failed_jobs),
                "failed": len(failed_jobs),
                "failed_jobs": failed_jobs,
                "results": summaries,
            },
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
