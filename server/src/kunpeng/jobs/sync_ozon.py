"""
Ozon 定时同步任务
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select

from kunpeng.config import settings
from kunpeng.core.database import AsyncSessionLocal
from kunpeng.core.scheduler import scheduler
from kunpeng.models.shop import Shop
from kunpeng.services.ozon_dwm_refresh_service import ozon_dwm_refresh_service
from kunpeng.services.ozon_product_translation_service import (
    ozon_product_translation_service,
)
from kunpeng.services.ozon_sync_service import OzonSyncService
from kunpeng.utils.timezone import now_platform

logger = logging.getLogger(__name__)


def _run_after(minutes: int) -> datetime:
    """Stagger startup work while keeping every interval at its original frequency."""
    return now_platform() + timedelta(minutes=minutes)


def _unfulfilled_cutoff_window(
    run_at: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """Return yesterday 00:00 through the actual run time in platform TZ."""
    window_end = run_at or now_platform()
    window_start = (
        window_end - timedelta(days=settings.sync.ozon_unfulfilled_lookback_days)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    return window_start, window_end


async def sync_all_shops_postings() -> Dict[str, Any]:
    """同步所有店铺的订单数据"""
    logger.info("[定时任务] 开始同步所有店铺订单数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Ozon 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        # 显式指定回看窗口（可配置，默认近 3 天），避免 service 兜底的 30 天大区间
        lookback_days = settings.sync.ozon_postings_lookback_days
        date_to = now_platform().strftime("%Y-%m-%d")
        date_from = (now_platform() - timedelta(days=lookback_days)).strftime(
            "%Y-%m-%d"
        )

        results = {}
        for shop in shops:
            logger.info(
                f"[定时任务] 同步店铺: {shop.id} - {shop.name}, 日期: {date_from} ~ {date_to}"
            )
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_postings(
                    date_from=date_from, date_to=date_to
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺订单数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_returns() -> Dict[str, Any]:
    """同步所有店铺的退货数据"""
    logger.info("[定时任务] 开始同步所有店铺退货数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Ozon 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                # 同步近 N 天退货数据（可配置，默认 2 天）
                lookback_days = settings.sync.ozon_returns_lookback_days
                date_to = now_platform().strftime("%Y-%m-%d")
                date_from = (now_platform() - timedelta(days=lookback_days)).strftime(
                    "%Y-%m-%d"
                )
                result = await sync_service.sync_returns(date_from, date_to)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺退货数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_reviews() -> Dict[str, Any]:
    """同步所有店铺的评价数据"""
    logger.info("[定时任务] 开始同步所有店铺评价数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Ozon 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_reviews()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺评价数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_finance() -> Dict[str, Any]:
    """同步所有店铺的财务数据"""
    logger.info("[定时任务] 开始同步所有店铺财务数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Ozon 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        # 财务应计存在延迟结算，显式回补 [今天-N, 昨天]（可配置，默认 7 天），幂等覆盖
        backfill_days = settings.sync.finance_backfill_days
        date_from = (now_platform() - timedelta(days=backfill_days)).strftime(
            "%Y-%m-%d"
        )
        date_to = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")

        results = {}
        for shop in shops:
            logger.info(
                f"[定时任务] 同步店铺: {shop.id} - {shop.name}, 日期: {date_from} ~ {date_to}"
            )
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_finance_accruals(
                    date_from=date_from, date_to=date_to
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺财务数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_accrual_types() -> Dict[str, Any]:
    """同步所有店铺的应计类型数据（维度数据，每天一次）"""
    logger.info("[定时任务] 开始同步所有店铺应计类型数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Ozon 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_accrual_types()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺应计类型数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_products() -> Dict[str, Any]:
    """同步所有店铺的商品信息（维度数据，每天一次）"""
    logger.info("[定时任务] 开始同步所有店铺商品信息")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_products()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺商品信息同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_adverts() -> Dict[str, Any]:
    """同步所有店铺的广告数据（Performance API，每天一次）"""
    logger.info("[定时任务] 开始同步所有店铺广告数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                # 同步近 7 天广告数据（覆盖延迟归因）
                date_to = now_platform().strftime("%Y-%m-%d")
                date_from = (now_platform() - timedelta(days=7)).strftime("%Y-%m-%d")
                result = await sync_service.sync_adverts(date_from, date_to)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_fbo_postings() -> Dict[str, Any]:
    """同步所有店铺的 FBO 订单数据（每小时）"""
    logger.info("[定时任务] 开始同步所有店铺FBO订单数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                # 同步近 N 天 FBO 订单（可配置，默认 3 天）
                lookback_days = settings.sync.ozon_fbo_lookback_days
                date_to = now_platform().strftime("%Y-%m-%d")
                date_from = (now_platform() - timedelta(days=lookback_days)).strftime(
                    "%Y-%m-%d"
                )
                result = await sync_service.sync_fbo_postings(date_from, date_to)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺FBO订单数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_unfulfilled_postings() -> Dict[str, Any]:
    """同步所有店铺的待处理（未发货）FBS 新订单数据（每小时）

    数据源 POST /v4/posting/fbs/unfulfilled/list，返回卖家仍需组装/
    发货的新订单。完整拉取游标分页后才对账，不物理删除历史记录。
    """
    logger.info("[定时任务] 开始同步所有店铺待处理新订单数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        # cutoff 是履约截止时间，不是订单创建时间。
        # 统一使用本轮开始时刻，窗口为莫斯科时间昨天零点到当前。
        window_start, window_end = _unfulfilled_cutoff_window()

        results = {}
        for shop in shops:
            logger.info(
                "[定时任务] 同步店铺: %s - %s, cutoff窗口: %s ~ %s",
                shop.id,
                shop.name,
                window_start,
                window_end,
            )
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_unfulfilled_postings(
                    window_start=window_start,
                    window_end=window_end,
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 待处理新订单失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺待处理新订单数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_advert_products() -> Dict[str, Any]:
    """同步所有店铺的广告SKU明细（异步报表，每天一次，耗时任务）"""
    logger.info("[定时任务] 开始同步所有店铺广告SKU明细")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                date_to = now_platform().strftime("%Y-%m-%d")
                date_from = (now_platform() - timedelta(days=7)).strftime("%Y-%m-%d")
                result = await sync_service.sync_advert_products(date_from, date_to)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告SKU明细同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_advert_products_hourly() -> Dict[str, Any]:
    """同步所有店铺的广告SKU明细（小时维度，每小时一次）"""
    logger.info("[定时任务] 开始同步所有店铺广告SKU小时明细")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Ozon 店铺")
            return {"status": "success", "message": "No Ozon shops found", "count": 0}

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = OzonSyncService(db, shop)
                result = await sync_service.sync_advert_products_hourly()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 广告SKU小时明细失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告SKU小时明细同步完成: {results}")
        return {"status": "success", "results": results}


async def translate_ozon_product_names() -> Dict[str, Any]:
    """Translate each Ozon shop/SKU product name at most once."""
    logger.info("[定时任务] 开始回填Ozon商品中文名称")
    async with AsyncSessionLocal() as db:
        try:
            result = await ozon_product_translation_service.translate_all_missing(
                db,
                batch_size=500,
                max_batches=10,
            )
            logger.info("[定时任务] Ozon商品中文名称回填完成: %s", result)
            return {"status": "success", **result}
        except Exception as exc:
            await db.rollback()
            logger.exception("[定时任务] Ozon商品中文名称回填失败")
            return {"status": "error", "message": str(exc)}


async def sync_all_shops_analytics_data() -> Dict[str, Any]:
    """回补所有 Ozon 店铺最近完整平台日的 SKU 日经营分析。"""
    lookback_days = settings.sync.ozon_analytics_lookback_days
    if not 1 <= lookback_days <= 31:
        return {
            "status": "error",
            "message": "SYNC_OZON_ANALYTICS_LOOKBACK_DAYS 必须在 1 到 31 之间",
        }

    platform_today = now_platform().date()
    date_to = platform_today - timedelta(days=1)
    date_from = date_to - timedelta(days=lookback_days - 1)
    date_from_text = date_from.isoformat()
    date_to_text = date_to.isoformat()
    logger.info(
        "[定时任务] 开始同步所有 Ozon 店铺经营分析，日期: %s ~ %s",
        date_from_text,
        date_to_text,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "ozon"))
        shops = list(result.scalars().all())
        if not shops:
            return {
                "status": "success",
                "message": "No Ozon shops found",
                "count": 0,
            }

        # Do not keep the shop-list SELECT transaction checked out while the
        # minute-limited API is paginating.  A large shop can spend several
        # minutes fetching data before the first database write.
        db.expunge_all()
        await db.rollback()

        results: Dict[int, Any] = {}
        failed = 0
        for index, shop in enumerate(shops):
            if index:
                # Each service owns its own limiter. Keep a conservative gap
                # at shop boundaries so a recently used Client-Id cannot make
                # the next run start inside Ozon's one-call/minute window.
                await asyncio.sleep(65)
            logger.info(
                "[定时任务] 同步 Ozon 经营分析店铺: %s - %s", shop.id, shop.name
            )
            sync_service = OzonSyncService(db, shop)
            shop_result = await sync_service.sync_analytics_data(
                date_from_text, date_to_text
            )
            results[shop.id] = shop_result
            if shop_result.get("status") != "success":
                failed += 1

        status = "success"
        if failed == len(shops):
            status = "error"
        elif failed:
            status = "partial_error"
        return {
            "status": status,
            "results": results,
            "shops": len(shops),
            "failed_shops": failed,
            "date_from": date_from_text,
            "date_to": date_to_text,
        }


async def refresh_ozon_dwm_tables() -> Dict[str, Any]:
    """Backfill and incrementally refresh both Ozon DWM tables."""
    logger.info("[定时任务] 开始刷新 Ozon DWM 表")
    async with AsyncSessionLocal() as db:
        try:
            result = await ozon_dwm_refresh_service.refresh_all(db)
            logger.info(
                "[定时任务] Ozon DWM 刷新完成: 历史退货日期段=%s",
                result["historical_return_range_count"],
            )
            return result
        except Exception as exc:
            logger.exception("[定时任务] Ozon DWM 刷新失败")
            return {"status": "error", "message": str(exc)}


def register_ozon_jobs() -> None:
    """注册 Ozon 定时任务（仅生产环境）"""
    from kunpeng.config import settings

    if settings.environment != "production" and not settings.jobs_enabled:
        logger.info(
            f"[Ozon] 当前环境为 {settings.environment} 且 jobs_enabled=False，跳过注册定时任务"
        )
        return

    # 每小时同步订单数据
    scheduler.add_interval_job(
        sync_all_shops_postings,
        minutes=60,
        job_id="ozon_sync_postings_hourly",
        name="Ozon 订单数据同步（每小时）",
        next_run_time=_run_after(3),
    )

    # 每小时同步 FBO 订单数据
    scheduler.add_interval_job(
        sync_all_shops_fbo_postings,
        minutes=60,
        job_id="ozon_sync_fbo_postings_hourly",
        name="Ozon FBO订单数据同步（每小时）",
        next_run_time=_run_after(5),
    )

    # 每小时同步待处理（未发货）新订单数据 —— 供下游识别增量新订单并提醒
    scheduler.add_interval_job(
        sync_all_shops_unfulfilled_postings,
        minutes=60,
        job_id="ozon_sync_unfulfilled_postings_hourly",
        name="Ozon 待处理新订单同步（每小时）",
        next_run_time=_run_after(1),
    )

    # 每小时同步退货数据
    scheduler.add_interval_job(
        sync_all_shops_returns,
        minutes=60,
        job_id="ozon_sync_returns_hourly",
        name="Ozon 退货数据同步（每小时）",
        next_run_time=_run_after(7),
    )

    # 每小时同步评价数据（供下游识别增量客户声音）
    scheduler.add_interval_job(
        sync_all_shops_reviews,
        minutes=60,
        job_id="ozon_sync_reviews_hourly",
        name="Ozon 评价数据同步（每小时）",
        next_run_time=_run_after(9),
    )

    # 每小时在订单、退货等上游任务之后刷新两张 Ozon DWM 表。
    # 首次运行会按日期分段回补已有 DWD 历史数据。
    scheduler.add_interval_job(
        refresh_ozon_dwm_tables,
        minutes=60,
        job_id="ozon_refresh_dwm_hourly",
        name="Ozon DWM 自动回补与增量刷新（每小时）",
        next_run_time=_run_after(15),
    )

    # 每天同步财务数据
    scheduler.add_cron_job(
        sync_all_shops_finance,
        cron="20 3 * * *",
        job_id="ozon_sync_finance_daily",
        name="Ozon 财务数据同步（每天3:20）",
    )

    # 每天同步应计类型数据（维度数据）
    scheduler.add_cron_job(
        sync_all_shops_accrual_types,
        cron="10 4 * * *",
        job_id="ozon_sync_accrual_types_daily",
        name="Ozon 应计类型数据同步（每天4:10）",
    )

    # 每天同步商品信息（维度数据）
    scheduler.add_cron_job(
        sync_all_shops_products,
        cron="30 4 * * *",
        job_id="ozon_sync_products_daily",
        name="Ozon 商品信息同步（每天）",
    )

    # 商品维度同步后回填中文名称；持久化缓存保证同一店铺SKU只翻译一次。
    scheduler.add_cron_job(
        translate_ozon_product_names,
        cron="45 4 * * *",
        job_id="ozon_translate_product_names_daily",
        name="Ozon 商品中文名称回填（每天）",
    )

    # 每天同步广告数据（Performance API）
    scheduler.add_cron_job(
        sync_all_shops_adverts,
        cron="0 5 * * *",
        job_id="ozon_sync_adverts_daily",
        name="Ozon 广告数据同步（每天）",
    )

    # 每天同步广告SKU明细（异步报表，耗时任务，安排在广告日统计之后）
    scheduler.add_cron_job(
        sync_all_shops_advert_products,
        cron="30 5 * * *",
        job_id="ozon_sync_advert_products_daily",
        name="Ozon 广告SKU明细同步（每天）",
    )

    # 每天莫斯科时间 7 点回补最近完整平台日的 SKU 日经营分析。
    scheduler.add_cron_job(
        sync_all_shops_analytics_data,
        cron="0 7 * * *",
        job_id="ozon_sync_analytics_data_daily",
        name="Ozon 经营分析SKU日数据同步（每天7:00）",
    )

    # 广告SKU明细小时同步 — 每小时第 10 分钟执行（口径对齐 WB 广告小时统计）
    scheduler.add_cron_job(
        sync_all_shops_advert_products_hourly,
        cron="10 * * * *",
        job_id="ozon_sync_advert_products_hourly",
        name="Ozon 广告SKU明细小时同步（每小时）",
    )

    logger.info("Ozon 定时任务已注册")
