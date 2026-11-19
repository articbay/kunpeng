"""
Wildberries 定时同步任务
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.config import settings
from kunpeng.core.database import AsyncSessionLocal
from kunpeng.core.scheduler import scheduler
from kunpeng.crud.dwd import (
    crud_dwd_wb_order_detail,
    crud_dwd_wb_order_statistics_detail,
    crud_dwd_wb_return_detail,
    crud_dwd_wb_voc_feedback_detail,
    crud_dwd_wb_voc_question_detail,
)
from kunpeng.models.shop import Shop
from kunpeng.services.wb_dwd_translation_service import wb_dwd_translation_service
from kunpeng.services.wb_dwm_refresh_service import wb_dwm_refresh_service
from kunpeng.services.wb_sync_service import WBSyncService
from kunpeng.utils.timezone import now_platform

logger = logging.getLogger(__name__)


def _run_after(minutes: int):
    """Stagger startup work while keeping every interval at its original frequency."""
    return now_platform() + timedelta(minutes=minutes)


def _get_region_sales_date_window(lookback_days: int) -> tuple[str, str]:
    """计算最近 N 个已结束完整平台日的闭区间。"""
    if lookback_days < 1 or lookback_days > 31:
        raise ValueError("lookback_days 必须为 1 至 31")
    date_to = (now_platform() - timedelta(days=1)).date()
    date_from = date_to - timedelta(days=lookback_days - 1)
    return date_from.isoformat(), date_to.isoformat()


def _get_product_search_texts_date_window(lookback_days: int) -> tuple[str, str]:
    """计算商品搜索词最近 N 个已结束完整平台日的闭区间。"""
    return _get_region_sales_date_window(lookback_days)


def _get_search_traffic_date_window(lookback_days: int) -> tuple[str, str]:
    """计算搜索流量最近 N 个已结束完整平台日的闭区间。"""
    return _get_region_sales_date_window(lookback_days)


def _get_previous_week_date_window() -> tuple[str, str]:
    """计算平台时区上一自然周（周一至周日）的闭区间。"""
    today = now_platform().date()
    current_week_monday = today - timedelta(days=today.weekday())
    date_to = current_week_monday - timedelta(days=1)
    date_from = date_to - timedelta(days=6)
    return date_from.isoformat(), date_to.isoformat()


async def sync_all_shops_sales() -> Dict[str, Any]:
    """同步所有店铺的销售数据"""
    logger.info("[定时任务] 开始同步所有店铺销售数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Wildberries 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 同步近 N 小时数据（可配置，默认 24h）
        lookback_hours = settings.sync.wb_orders_lookback_hours
        date_from = (now_platform() - timedelta(hours=lookback_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_sales(date_from, None)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺销售数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_orders() -> Dict[str, Any]:
    """同步所有店铺的订单数据"""
    logger.info("[定时任务] 开始同步所有店铺订单数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Wildberries 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 同步近 N 小时数据（可配置，默认 24h）
        lookback_hours = settings.sync.wb_orders_lookback_hours
        date_from = (now_platform() - timedelta(hours=lookback_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_orders(date_from, None)
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺订单数据同步完成: {results}")
        return {"status": "success", "results": results}


async def refresh_wb_order_lifecycle_dwm() -> Dict[str, Any]:
    """Refresh the WB order lifecycle DWM after hourly source syncs."""
    logger.info("[定时任务] 开始刷新 WB 订单生命周期 DWM")
    async with AsyncSessionLocal() as db:
        try:
            result = await wb_dwm_refresh_service.refresh_lifecycle_all(db)
            logger.info(
                "[定时任务] WB 订单生命周期 DWM 刷新完成: 历史退货日期段=%s",
                result["historical_return_range_count"],
            )
            return result
        except Exception as exc:
            logger.exception("[定时任务] WB 订单生命周期 DWM 刷新失败")
            return {"status": "error", "message": str(exc)}


async def sync_all_shops_adverts() -> Dict[str, Any]:
    """同步所有店铺的广告数据"""
    logger.info("[定时任务] 开始同步所有店铺广告数据")

    async with AsyncSessionLocal() as db:
        # 获取所有 Wildberries 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 同步 T-1 数据
        yesterday = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_adverts(
                    date_from=yesterday, date_to=yesterday
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_finance() -> Dict[str, Any]:
    """同步所有店铺的财务数据（每天早上9点执行，带回补窗口）

    平台财务/结算存在 T+1 甚至更晚的延迟结算，仅拉 T-1 可能漏数。
    这里回补 [今天-N, 昨天] 区间（N 可配置，默认 7 天），幂等覆盖。
    """
    backfill_days = settings.sync.finance_backfill_days
    date_from = (now_platform() - timedelta(days=backfill_days)).strftime("%Y-%m-%d")
    date_to = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"[定时任务] 开始同步所有店铺财务数据 (回补 {date_from} ~ {date_to})")

    async with AsyncSessionLocal() as db:
        # 获取所有 Wildberries 店铺
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(
                f"[定时任务] 同步店铺: {shop.id} - {shop.name}, 日期: {date_from} ~ {date_to}"
            )
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_finance(
                    date_from=date_from, date_to=date_to
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 财务数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺财务数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_finance_daily() -> Dict[str, Any]:
    """同步所有店铺的 WB 按日财务明细。"""
    backfill_days = settings.sync.wb_finance_daily_backfill_days
    date_from = (now_platform() - timedelta(days=backfill_days)).strftime("%Y-%m-%d")
    date_to = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(
        "[定时任务] 开始同步所有店铺按日财务明细 (%s ~ %s)",
        date_from,
        date_to,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())
        if not shops:
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_finance_daily(
                    date_from=date_from,
                    date_to=date_to,
                )
            except Exception as exc:
                logger.exception("[定时任务] 店铺 %s 按日财务同步失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(exc)}

        return {"status": "success", "results": results}


async def sync_all_shops_sales_report_list() -> Dict[str, Any]:
    """同步所有 Wildberries 店铺的上一自然周财务报表列表。"""
    date_from, date_to = _get_previous_week_date_window()
    logger.info(
        "[定时任务] 开始同步所有店铺财务报表列表 (%s ~ %s)",
        date_from,
        date_to,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_sales_report_list(
                    date_from,
                    date_to,
                )
            except Exception as e:
                logger.exception(
                    "[定时任务] 同步店铺 %s 财务报表列表失败: %s",
                    shop.id,
                    e,
                )
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺财务报表列表同步完成")
        return {
            "status": "success",
            "date_from": date_from,
            "date_to": date_to,
            "results": results,
        }


async def sync_all_shops_feedbacks() -> Dict[str, Any]:
    """同步所有店铺的评价数据（每天）"""
    logger.info("[定时任务] 开始同步所有店铺评价数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 计算 T-1 日期范围
        today = now_platform().strftime("%Y-%m-%d")
        yesterday = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_feedbacks(
                    date_from=yesterday, date_to=today
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 评价数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺评价数据同步完成: {results}")
        return {"status": "success", "results": results}


async def reconcile_wb_voc_feedback_dwd() -> Dict[str, Any]:
    """从ODS全量幂等校准Wildberries客户评价DWD表。"""
    logger.info("[定时任务] 开始全量校准Wildberries客户评价DWD表")

    async with AsyncSessionLocal() as db:
        try:
            result = await crud_dwd_wb_voc_feedback_detail.upsert_from_ods(db)
            translation = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info(
                "[定时任务] Wildberries客户评价DWD校准完成: %s",
                result,
            )
            return {"status": "success", **result, "translation": translation}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] Wildberries客户评价DWD校准失败")
            return {"status": "error", "message": str(error)}


async def reconcile_wb_voc_question_dwd() -> Dict[str, Any]:
    """从ODS全量幂等校准Wildberries客户提问DWD表。"""
    logger.info("[定时任务] 开始全量校准Wildberries客户提问DWD表")

    async with AsyncSessionLocal() as db:
        try:
            result = await crud_dwd_wb_voc_question_detail.upsert_from_ods(db)
            translation = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info(
                "[定时任务] Wildberries客户提问DWD校准完成: %s",
                result,
            )
            return {"status": "success", **result, "translation": translation}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] Wildberries客户提问DWD校准失败")
            return {"status": "error", "message": str(error)}


async def reconcile_wb_return_dwd() -> Dict[str, Any]:
    """从ODS全量幂等校准Wildberries退货DWD表。"""
    logger.info("[定时任务] 开始全量校准Wildberries退货DWD表")

    async with AsyncSessionLocal() as db:
        try:
            result = await crud_dwd_wb_return_detail.upsert_from_ods(db)
            translation = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info("[定时任务] Wildberries退货DWD校准完成: %s", result)
            return {"status": "success", **result, "translation": translation}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] Wildberries退货DWD校准失败")
            return {"status": "error", "message": str(error)}


async def reconcile_wb_order_dwd() -> Dict[str, Any]:
    """从ODS全量幂等校准Wildberries订单DWD表。"""
    logger.info("[定时任务] 开始全量校准Wildberries订单DWD表")

    async with AsyncSessionLocal() as db:
        try:
            result = await crud_dwd_wb_order_detail.upsert_from_ods(db)
            translation = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info("[定时任务] Wildberries订单DWD校准完成: %s", result)
            return {"status": "success", **result, "translation": translation}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] Wildberries订单DWD校准失败")
            return {"status": "error", "message": str(error)}


async def reconcile_wb_order_statistics_dwd() -> Dict[str, Any]:
    """从ODS全量幂等校准Wildberries统计订单DWD表。"""
    logger.info("[定时任务] 开始全量校准Wildberries统计订单DWD表")

    async with AsyncSessionLocal() as db:
        try:
            result = await crud_dwd_wb_order_statistics_detail.upsert_from_ods(db)
            translation = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info("[定时任务] Wildberries统计订单DWD校准完成: %s", result)
            return {"status": "success", **result, "translation": translation}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] Wildberries统计订单DWD校准失败")
            return {"status": "error", "message": str(error)}


async def translate_wb_dwd_to_chinese() -> Dict[str, Any]:
    """Incrementally backfill Chinese translations for marketplace DWD content."""
    logger.info("[定时任务] 开始回填WB/Ozon DWD中文翻译")
    async with AsyncSessionLocal() as db:
        try:
            result = await wb_dwd_translation_service.translate_all_missing(db)
            logger.info("[定时任务] WB/Ozon DWD中文翻译完成: %s", result)
            return {"status": "success", **result}
        except Exception as error:
            await db.rollback()
            logger.exception("[定时任务] WB/Ozon DWD中文翻译失败")
            return {"status": "error", "message": str(error)}


async def sync_all_shops_feedback_pins() -> Dict[str, Any]:
    """同步所有店铺昨天零点至当前的评价置顶记录。"""
    window_end = now_platform()
    window_start = (
        window_end - timedelta(days=settings.sync.wb_feedback_pins_lookback_days)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info(
        "[定时任务] 开始同步所有店铺评价置顶记录: %s ~ %s",
        window_start,
        window_end,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }

        results = {}
        for shop in shops:
            logger.info(
                "[定时任务] 同步店铺评价置顶记录: %s - %s",
                shop.id,
                shop.name,
            )
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_feedback_pins(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                await db.rollback()
                logger.exception(
                    "[定时任务] 同步店铺%s的评价置顶记录失败",
                    shop.id,
                )
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺评价置顶记录同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_questions() -> Dict[str, Any]:
    """同步所有店铺的问答数据（每天）"""
    logger.info("[定时任务] 开始同步所有店铺问答数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_questions()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 问答数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺问答数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_funnel() -> Dict[str, Any]:
    """按单日粒度回补所有店铺最近完整平台日的销售漏斗数据。"""
    logger.info("[定时任务] 开始同步所有店铺销售漏斗数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }
        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_funnel_lookback(
                    settings.sync.wb_funnel_lookback_days
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 销售漏斗数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺销售漏斗数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_returns() -> Dict[str, Any]:
    """同步所有店铺的退货数据（每天）"""
    logger.info("[定时任务] 开始同步所有店铺退货数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_returns()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 退货数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺退货数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_return_claims() -> Dict[str, Any]:
    """同步所有店铺最近一小时新增或变化的买家退货申请。"""
    window_end = now_platform()
    window_start = window_end - timedelta(
        hours=settings.sync.wb_return_claims_lookback_hours
    )
    logger.info(
        "[定时任务] 开始同步所有店铺买家退货申请: %s ~ %s",
        window_start.isoformat(),
        window_end.isoformat(),
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())
        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_return_claims(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 买家退货申请失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺买家退货申请同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_chat_events() -> Dict[str, Any]:
    """同步所有店铺从昨天零点到当前时刻的买家聊天事件。"""
    window_end = now_platform()
    window_start = (
        window_end - timedelta(days=settings.sync.wb_chat_events_lookback_days)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info(
        "[定时任务] 开始同步所有店铺买家聊天事件: %s ~ %s",
        window_start.isoformat(),
        window_end.isoformat(),
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())
        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_chat_events(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 买家聊天事件失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺买家聊天事件同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_marketplace_orders() -> Dict[str, Any]:
    """同步所有店铺的 Marketplace 订单数据（每小时）"""
    logger.info("[定时任务] 开始同步所有店铺 Marketplace 订单数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 显式指定回看窗口（可配置，默认近 2 天），避免依赖 service 兜底的大区间
        lookback_days = settings.sync.wb_marketplace_lookback_days
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
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_marketplace_orders(
                    date_from=date_from, date_to=date_to
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} Marketplace 订单失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺 Marketplace 订单同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_new_orders() -> Dict[str, Any]:
    """同步所有店铺的新订单（待处理组装订单）数据（每小时）

    数据源 GET /api/v3/orders/new，返回"当前所有待卖家处理的新订单"，
    无日期参数、不分页。只 upsert 不删除，配合 first_seen_at 供下游
    （如 Hermes 智能体）识别增量新订单并及时提醒。
    """
    logger.info("[定时任务] 开始同步所有店铺新订单数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_new_orders()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 新订单失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺新订单数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_fbs_supplies() -> Dict[str, Any]:
    """同步所有店铺的FBS供货单，并统计昨天零点至当前的业务窗口。"""
    window_end = now_platform()
    window_start = (window_end - timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    logger.info(
        "[定时任务] 开始同步所有店铺FBS供货单: %s ~ %s",
        window_start,
        window_end,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }

        results = {}
        for shop in shops:
            logger.info(
                "[定时任务] 同步店铺FBS供货单: %s - %s",
                shop.id,
                shop.name,
            )
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_fbs_supplies(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺%s的FBS供货单失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺FBS供货单同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_reshipment_orders() -> Dict[str, Any]:
    """同步所有店铺当前需要重新发货的订单状态快照。"""
    window_end = now_platform()
    window_start = (
        window_end - timedelta(days=settings.sync.wb_reshipment_lookback_days)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info(
        "[定时任务] 开始同步所有店铺重新发货订单: %s ~ %s",
        window_start,
        window_end,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }

        results = {}
        for shop in shops:
            logger.info(
                "[定时任务] 同步店铺重新发货订单: %s - %s",
                shop.id,
                shop.name,
            )
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_reshipment_orders(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                await db.rollback()
                logger.exception(
                    "[定时任务] 同步店铺%s的重新发货订单失败",
                    shop.id,
                )
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺重新发货订单同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_order_metadata() -> Dict[str, Any]:
    """补全所有店铺昨天零点至当前的 Marketplace 订单元数据。"""
    window_end = now_platform()
    window_start = (
        window_end - timedelta(days=settings.sync.wb_order_metadata_lookback_days)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info(
        "[定时任务] 开始同步所有店铺订单元数据: %s ~ %s",
        window_start,
        window_end,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }

        results = {}
        for shop in shops:
            logger.info(
                "[定时任务] 同步店铺订单元数据: %s - %s",
                shop.id,
                shop.name,
            )
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_order_metadata(
                    window_start=window_start,
                    window_end=window_end,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 订单元数据失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺订单元数据同步完成: %s", results)
        return {
            "status": "success",
            "results": results,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }


async def sync_all_shops_balance() -> Dict[str, Any]:
    """同步所有店铺的余额数据（每天早上8点）"""
    logger.info("[定时任务] 开始同步所有店铺余额数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_balance()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 余额失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺余额同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_seller_balance() -> Dict[str, Any]:
    """同步所有 Wildberries 店铺的财务域卖家余额。"""
    logger.info("[定时任务] 开始同步所有店铺卖家余额")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info("[定时任务] 同步店铺卖家余额: %s - %s", shop.id, shop.name)
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_seller_balance()
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 卖家余额失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺卖家余额同步完成: %s", results)
        return {"status": "success", "results": results}


async def sync_all_shops_region_sales() -> Dict[str, Any]:
    """同步所有 Wildberries 店铺最近已结束的完整平台日区域销售报告。"""
    lookback_days = settings.sync.wb_region_sales_lookback_days
    try:
        date_from_str, date_to_str = _get_region_sales_date_window(lookback_days)
    except ValueError:
        return {
            "status": "error",
            "message": "sync.wb_region_sales_lookback_days 必须为 1 至 31",
        }
    logger.info(
        "[定时任务] 开始同步所有店铺区域销售报告，窗口: %s~%s",
        date_from_str,
        date_to_str,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info("[定时任务] 同步店铺区域销售报告: %s - %s", shop.id, shop.name)
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_region_sales(
                    date_from_str,
                    date_to_str,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 区域销售报告失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info("[定时任务] 所有店铺区域销售报告同步完成: %s", results)
        return {
            "status": "success",
            "date_from": date_from_str,
            "date_to": date_to_str,
            "results": results,
        }


async def sync_all_shops_product_search_texts() -> Dict[str, Any]:
    """同步所有 Wildberries 店铺最近两个完整平台日的商品搜索词。"""
    lookback_days = settings.sync.wb_product_search_texts_lookback_days
    try:
        date_from_str, date_to_str = _get_product_search_texts_date_window(
            lookback_days
        )
    except ValueError:
        return {
            "status": "error",
            "message": "sync.wb_product_search_texts_lookback_days 必须为 1 至 31",
        }

    logger.info(
        "[定时任务] 开始同步所有店铺商品搜索词，窗口: %s~%s",
        date_from_str,
        date_to_str,
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())
        if not shops:
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_product_search_texts(
                    date_from_str,
                    date_to_str,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 商品搜索词失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}
        return {
            "status": "success",
            "date_from": date_from_str,
            "date_to": date_to_str,
            "results": results,
        }


async def sync_all_shops_search_traffic() -> Dict[str, Any]:
    """同步所有 Wildberries 店铺最近七个完整平台日的搜索流量。"""
    lookback_days = settings.sync.wb_search_traffic_lookback_days
    try:
        date_from_str, date_to_str = _get_search_traffic_date_window(lookback_days)
    except ValueError:
        return {
            "status": "error",
            "message": "sync.wb_search_traffic_lookback_days 必须为 1 至 31",
        }

    logger.info(
        "[定时任务] 开始同步所有店铺搜索流量，窗口: %s~%s",
        date_from_str,
        date_to_str,
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())
        if not shops:
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            try:
                sync_service = WBSyncService(db, shop)
                results[shop.id] = await sync_service.sync_search_traffic(
                    date_from_str,
                    date_to_str,
                )
            except Exception as e:
                logger.exception("[定时任务] 同步店铺 %s 搜索流量失败", shop.id)
                results[shop.id] = {"status": "error", "message": str(e)}
        return {
            "status": "success",
            "date_from": date_from_str,
            "date_to": date_to_str,
            "results": results,
        }


async def sync_all_shops_advert_stats_hourly() -> Dict[str, Any]:
    """同步所有店铺的广告统计（小时维度）"""
    logger.info("[定时任务] 开始同步所有店铺广告小时统计")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_advert_stats_hourly()
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 广告小时统计失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告小时统计同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_search_cluster_stat_hourly() -> Dict[str, Any]:
    """同步所有店铺的搜索关键字统计（小时维度）"""
    logger.info("[定时任务] 开始同步所有店铺搜索关键字小时统计")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_search_cluster_stat_hourly()
                results[shop.id] = result
            except Exception as e:
                logger.error(
                    f"[定时任务] 同步店铺 {shop.id} 搜索关键字小时统计失败: {e}"
                )
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺搜索关键字小时统计同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_adv_enhanced() -> Dict[str, Any]:
    """同步所有店铺的增强广告数据(8个新API)（每天凌晨3点）"""
    logger.info("[定时任务] 开始同步所有店铺增强广告数据")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 同步T-1数据
        yesterday = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_adv_enhanced(
                    date_from=yesterday, date_to=yesterday
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 增强广告数据失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺增强广告数据同步完成: {results}")
        return {"status": "success", "results": results}


async def sync_all_shops_advert_fullstats() -> Dict[str, Any]:
    """同步所有店铺的广告完整统计数据（每小时第10分钟）"""
    logger.info("[定时任务] 开始同步所有店铺广告完整统计")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        # 同步T-1和今天的数据
        yesterday = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = now_platform().strftime("%Y-%m-%d")

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 同步店铺: {shop.id} - {shop.name}")
            try:
                sync_service = WBSyncService(db, shop)
                result = await sync_service.sync_advert_fullstats(
                    date_from=yesterday, date_to=today
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 同步店铺 {shop.id} 广告完整统计失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告完整统计同步完成: {results}")
        return {"status": "success", "results": results}


async def refresh_all_shops_adverts_report() -> Dict[str, Any]:
    """刷新所有店铺的广告周度报表（每天凌晨2:30，ods_wb_advert_stats更新后30分钟）"""
    logger.info("[定时任务] 开始刷新所有店铺广告周度报表")

    from kunpeng.crud.dwd.wildberries.adverts_report import (
        crud_dwd_wb_adverts_report_detail,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Shop).where(Shop.platform == "wildberries"))
        shops = list(result.scalars().all())

        if not shops:
            logger.info("[定时任务] 没有找到 Wildberries 店铺")
            return {
                "status": "success",
                "message": "No Wildberries shops found",
                "count": 0,
            }

        results = {}
        for shop in shops:
            logger.info(f"[定时任务] 刷新报表: {shop.id} - {shop.name}")
            try:
                result = await crud_dwd_wb_adverts_report_detail.refresh_weekly_report(
                    db, shop.id, week_str=None
                )
                results[shop.id] = result
            except Exception as e:
                logger.error(f"[定时任务] 刷新店铺 {shop.id} 报表失败: {e}")
                results[shop.id] = {"status": "error", "message": str(e)}

        logger.info(f"[定时任务] 所有店铺广告周度报表刷新完成: {results}")
        return {"status": "success", "results": results}


def register_wildberries_jobs() -> None:
    """注册 Wildberries 定时任务（仅生产环境）"""
    from kunpeng.config import settings

    if settings.environment != "production" and not settings.jobs_enabled:
        logger.info(
            f"[Wildberries] 当前环境为 {settings.environment} 且 jobs_enabled=False，跳过注册定时任务"
        )
        return

    # 每小时同步销售数据
    scheduler.add_interval_job(
        sync_all_shops_sales,
        minutes=60,
        job_id="wb_sync_sales_hourly",
        name="Wildberries 销售数据同步（每小时）",
        next_run_time=_run_after(6),
    )

    # 每小时同步订单数据
    scheduler.add_interval_job(
        sync_all_shops_orders,
        minutes=60,
        job_id="wb_sync_orders_hourly",
        name="Wildberries 订单数据同步（每小时）",
        next_run_time=_run_after(8),
    )

    # 每天同步广告数据
    scheduler.add_cron_job(
        sync_all_shops_adverts,
        cron="0 2 * * *",  # 每天凌晨 2 点
        job_id="wb_sync_adverts_daily",
        name="Wildberries 广告数据同步（每天）",
    )

    # 每天早上9点同步财务数据（T-1）
    scheduler.add_cron_job(
        sync_all_shops_finance,
        cron="0 9 * * *",  # 每天早上 9 点
        job_id="wb_sync_finance_daily",
        name="Wildberries 财务数据同步（每天9点，T-1）",
    )

    scheduler.add_cron_job(
        sync_all_shops_finance_daily,
        cron="0 10 * * *",
        job_id="wb_sync_finance_daily_by_day",
        name="Wildberries 财务数据同步（按天维度，每天10点，T-1）",
    )

    # 每小时同步评价数据（供下游识别增量客户声音）
    scheduler.add_interval_job(
        sync_all_shops_feedbacks,
        minutes=60,
        job_id="wb_sync_feedbacks_hourly",
        name="Wildberries 评价数据同步（每小时）",
        next_run_time=_run_after(10),
    )

    # 启动后错峰校准一次，之后每天凌晨3:30全量兜底校准
    scheduler.add_cron_job(
        reconcile_wb_voc_feedback_dwd,
        cron="30 3 * * *",
        job_id="wb_reconcile_voc_feedback_dwd_daily",
        name="Wildberries 客户评价DWD全量校准（每天3:30）",
        next_run_time=_run_after(30),
    )

    # 调度进程启动后错峰补跑一次，之后每天莫斯科时间凌晨3点执行
    scheduler.add_cron_job(
        sync_all_shops_feedback_pins,
        cron="0 3 * * *",
        job_id="wb_sync_feedback_pins_daily",
        name="Wildberries 评价置顶记录同步（每天3点）",
        next_run_time=_run_after(20),
    )

    # 每小时同步问答数据（供下游识别增量客户声音）
    scheduler.add_interval_job(
        sync_all_shops_questions,
        minutes=60,
        job_id="wb_sync_questions_hourly",
        name="Wildberries 问答数据同步（每小时）",
        next_run_time=_run_after(12),
    )

    # 启动后错峰校准一次，之后每天凌晨3:35全量兜底校准
    scheduler.add_cron_job(
        reconcile_wb_voc_question_dwd,
        cron="35 3 * * *",
        job_id="wb_reconcile_voc_question_dwd_daily",
        name="Wildberries 客户提问DWD全量校准（每天3:35）",
        next_run_time=_run_after(32),
    )

    # 每天凌晨4点同步销售漏斗数据
    scheduler.add_cron_job(
        sync_all_shops_funnel,
        cron="0 4 * * *",  # 每天凌晨 4 点
        job_id="wb_sync_funnel_daily",
        name="Wildberries 销售漏斗数据同步（每天）",
    )

    # 每小时同步退货数据（供下游识别增量退货）
    scheduler.add_interval_job(
        sync_all_shops_returns,
        minutes=60,
        job_id="wb_sync_returns_hourly",
        name="Wildberries 退货数据同步（每小时）",
        next_run_time=_run_after(14),
    )

    # 启动后错峰校准一次，之后每天凌晨3:40全量兜底校准
    scheduler.add_cron_job(
        reconcile_wb_return_dwd,
        cron="40 3 * * *",
        job_id="wb_reconcile_return_dwd_daily",
        name="Wildberries 退货DWD全量校准（每天3:40）",
        next_run_time=_run_after(34),
    )

    # 启动调度进程后立即同步一次，之后每 60 分钟同步最近一小时
    scheduler.add_interval_job(
        sync_all_shops_return_claims,
        minutes=60,
        job_id="wb_sync_return_claims_hourly",
        name="Wildberries 买家退货申请同步（每小时）",
        next_run_time=_run_after(0),
    )

    # 启动调度进程后第 2 分钟同步一次，之后每 60 分钟同步昨天零点至当前
    scheduler.add_interval_job(
        sync_all_shops_chat_events,
        minutes=60,
        job_id="wb_sync_chat_events_hourly",
        name="Wildberries 买家聊天事件同步（每小时）",
        next_run_time=_run_after(2),
    )

    # 每小时同步 Marketplace 订单数据
    scheduler.add_interval_job(
        sync_all_shops_marketplace_orders,
        minutes=60,
        job_id="wb_sync_marketplace_orders_hourly",
        name="Wildberries Marketplace 订单同步（每小时）",
        next_run_time=_run_after(16),
    )

    # 在销售、订单、退货和 Marketplace 上游任务之后刷新生命周期 DWM。
    scheduler.add_interval_job(
        refresh_wb_order_lifecycle_dwm,
        minutes=60,
        job_id="wb_refresh_order_lifecycle_dwm_hourly",
        name="WB 订单生命周期 DWM 自动回补与增量刷新（每小时）",
        next_run_time=_run_after(20),
    )

    # 启动后错峰校准一次，之后每天凌晨3:45/3:50全量兜底校准
    scheduler.add_cron_job(
        reconcile_wb_order_dwd,
        cron="45 3 * * *",
        job_id="wb_reconcile_order_dwd_daily",
        name="Wildberries 订单DWD全量校准（每天3:45）",
        next_run_time=_run_after(36),
    )

    scheduler.add_cron_job(
        reconcile_wb_order_statistics_dwd,
        cron="50 3 * * *",
        job_id="wb_reconcile_order_statistics_dwd_daily",
        name="Wildberries 统计订单DWD全量校准（每天3:50）",
        next_run_time=_run_after(38),
    )

    scheduler.add_interval_job(
        translate_wb_dwd_to_chinese,
        minutes=15,
        job_id="wb_translate_dwd_cn_every_15_minutes",
        name="WB/Ozon DWD俄语转中文（每15分钟）",
        next_run_time=_run_after(4),
    )

    # 每小时同步新订单（待处理组装订单）数据 —— 供下游识别增量新订单并提醒
    scheduler.add_interval_job(
        sync_all_shops_new_orders,
        minutes=60,
        job_id="wb_sync_new_orders_hourly",
        name="Wildberries 新订单同步（每小时）",
        next_run_time=_run_after(18),
    )

    # 调度进程启动后错峰补跑一次，之后每天莫斯科时间凌晨 3:05 执行
    scheduler.add_cron_job(
        sync_all_shops_order_metadata,
        cron="5 3 * * *",
        job_id="wb_sync_order_metadata_daily",
        name="Wildberries 订单元数据同步（每天3:05）",
        next_run_time=_run_after(22),
    )

    # 调度进程启动后错峰补跑一次，之后每天莫斯科时间凌晨3:10执行
    scheduler.add_cron_job(
        sync_all_shops_fbs_supplies,
        cron="10 3 * * *",
        job_id="wb_sync_fbs_supplies_daily",
        name="Wildberries FBS供货单同步（每天3:10）",
        next_run_time=_run_after(24),
    )

    # 调度进程启动后错峰补跑一次，之后每天莫斯科时间凌晨3:15执行
    scheduler.add_cron_job(
        sync_all_shops_reshipment_orders,
        cron="15 3 * * *",
        job_id="wb_sync_reshipment_orders_daily",
        name="Wildberries 重新发货订单同步（每天3:15）",
        next_run_time=_run_after(26),
    )

    # 每天早上8点同步余额数据
    scheduler.add_cron_job(
        sync_all_shops_balance,
        cron="0 8 * * *",  # 每天早上 8 点
        job_id="wb_sync_balance_daily",
        name="Wildberries 余额同步（每天8点）",
    )

    # 每天凌晨3点同步财务域卖家余额快照
    scheduler.add_cron_job(
        sync_all_shops_seller_balance,
        cron="0 3 * * *",
        job_id="wb_sync_seller_balance_daily",
        name="Wildberries 卖家余额同步（每天3点）",
    )

    # 每周一凌晨3:05同步上一自然周的财务报表列表。
    scheduler.add_cron_job(
        sync_all_shops_sales_report_list,
        cron="5 3 * * mon",
        job_id="wb_sync_sales_report_list_weekly",
        name="Wildberries 财务报表列表同步（每周一3:05）",
    )

    # 每天凌晨3:05同步最近两个完整平台日的区域销售报告
    scheduler.add_cron_job(
        sync_all_shops_region_sales,
        cron="5 3 * * *",
        job_id="wb_sync_region_sales_daily",
        name="Wildberries 区域销售报告同步（每天3:05）",
    )

    # 每天凌晨3:15同步最近七个完整平台日的商品搜索流量
    scheduler.add_cron_job(
        sync_all_shops_search_traffic,
        cron="15 3 * * *",
        job_id="wb_sync_search_traffic_daily",
        name="Wildberries 搜索流量同步（每天3:15）",
    )

    # 每天凌晨3:35同步最近两个完整平台日的商品自然搜索词
    scheduler.add_cron_job(
        sync_all_shops_product_search_texts,
        cron="35 3 * * *",
        job_id="wb_sync_product_search_texts_daily",
        name="Wildberries 商品搜索词同步（每天3:35）",
    )

    # 广告统计小时同步 — 每小时第 5 分钟执行
    scheduler.add_cron_job(
        sync_all_shops_advert_stats_hourly,
        cron="5 * * * *",
        job_id="wb_sync_advert_stats_hourly",
        name="Wildberries 广告统计小时同步（每小时）",
    )

    # 搜索词统计小时同步 — 每小时第 7 分钟执行
    scheduler.add_cron_job(
        sync_all_shops_search_cluster_stat_hourly,
        cron="7 * * * *",
        job_id="wb_sync_search_cluster_stat_hourly",
        name="Wildberries 搜索关键字统计小时同步（每小时第7分钟）",
    )

    # 增强广告数据同步 — 每天凌晨3点
    scheduler.add_cron_job(
        sync_all_shops_adv_enhanced,
        cron="0 3 * * *",
        job_id="wb_sync_adv_enhanced_daily",
        name="Wildberries 增强广告数据同步（每天3点）",
    )

    # 广告完整统计同步 — 每小时第10分钟
    scheduler.add_cron_job(
        sync_all_shops_advert_fullstats,
        cron="10 * * * *",
        job_id="wb_sync_advert_fullstats_hourly",
        name="Wildberries 广告完整统计同步（每小时）",
    )

    # 广告周度报表刷新 — 每天凌晨2:30（ods_wb_advert_stats更新后30分钟）
    scheduler.add_cron_job(
        refresh_all_shops_adverts_report,
        cron="30 2 * * *",
        job_id="wb_refresh_adverts_report_daily",
        name="Wildberries 广告周度报表刷新（每天）",
    )

    logger.info("Wildberries 定时任务已注册")
