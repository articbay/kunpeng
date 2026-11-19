"""
调度任务集成测试

真实调用 API 并写入数据库，验证各平台同步任务可正常运行。

用法:
    # 运行所有集成测试
    poetry run pytest tests/integration/ -v

    # 只测试 Wildberries 任务
    poetry run pytest tests/integration/test_jobs.py -v -k wb

    # 只测试 Ozon 任务
    poetry run pytest tests/integration/test_jobs.py -v -k ozon

    # 只测试指定任务
    poetry run pytest tests/integration/test_jobs.py -v -k sales

    # 排除集成测试（只跑单元测试）
    poetry run pytest -v -m "not integration"

注意:
    - 测试会真实调用外部 API 并写入数据库
    - 确保 .env 中的 API 配置正确
    - 建议在非高峰时段执行
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

import pytest

from kunpeng.jobs.sync_ozon import sync_all_shops_accrual_types
from kunpeng.jobs.sync_ozon import (
    sync_all_shops_advert_products as sync_all_shops_ozon_advert_products,
)
from kunpeng.jobs.sync_ozon import sync_all_shops_adverts as sync_all_shops_ozon_adverts
from kunpeng.jobs.sync_ozon import sync_all_shops_fbo_postings
from kunpeng.jobs.sync_ozon import sync_all_shops_finance as sync_all_shops_ozon_finance
from kunpeng.jobs.sync_ozon import sync_all_shops_postings
from kunpeng.jobs.sync_ozon import (
    sync_all_shops_products as sync_all_shops_ozon_products,
)
from kunpeng.jobs.sync_ozon import sync_all_shops_returns as sync_all_shops_ozon_returns
from kunpeng.jobs.sync_ozon import sync_all_shops_reviews

# 导入所有 Job 函数
from kunpeng.jobs.sync_wildberries import (
    sync_all_shops_advert_stats_hourly,
    sync_all_shops_adverts,
    sync_all_shops_balance,
    sync_all_shops_chat_events,
    sync_all_shops_fbs_supplies,
    sync_all_shops_feedback_pins,
    sync_all_shops_feedbacks,
    sync_all_shops_finance,
    sync_all_shops_funnel,
    sync_all_shops_marketplace_orders,
    sync_all_shops_order_metadata,
    sync_all_shops_orders,
    sync_all_shops_questions,
    sync_all_shops_reshipment_orders,
    sync_all_shops_return_claims,
    sync_all_shops_returns,
    sync_all_shops_sales,
    sync_all_shops_search_cluster_stat_hourly,
)

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# 辅助函数
# ───────────────────────────────────────────────


async def _run_job(job_func: Callable, name: str) -> Dict[str, Any]:
    """执行单个 Job，记录耗时并返回结果"""
    start = datetime.now()
    logger.info(f"▶️  开始执行: {name}")

    try:
        result = await job_func()
        elapsed = (datetime.now() - start).total_seconds()
        status = result.get("status", "unknown")

        if status == "success":
            logger.info(f"✅ {name} 成功 ({elapsed:.2f}s)")
        elif status == "skipped":
            logger.info(f"⏭️  {name} 已跳过 ({elapsed:.2f}s)")
        else:
            logger.warning(f"⚠️  {name} 状态: {status} ({elapsed:.2f}s)")

        return {"name": name, "status": status, "result": result, "elapsed": elapsed}

    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        logger.exception(f"💥 {name} 异常 ({elapsed:.2f}s)")
        return {
            "name": name,
            "status": "exception",
            "error": str(e),
            "elapsed": elapsed,
        }


# ───────────────────────────────────────────────
# Wildberries 基础同步任务
# ───────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_sales():
    """WB 销售数据同步"""
    r = await _run_job(sync_all_shops_sales, "WB sales")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_orders():
    """WB 订单数据同步"""
    r = await _run_job(sync_all_shops_orders, "WB orders")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_adverts():
    """WB 广告数据同步"""
    r = await _run_job(sync_all_shops_adverts, "WB adverts")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_finance():
    """WB 财务数据同步 (T-1)"""
    r = await _run_job(sync_all_shops_finance, "WB finance")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_feedbacks():
    """WB 评价数据同步"""
    r = await _run_job(sync_all_shops_feedbacks, "WB feedbacks")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_questions():
    """WB 问答数据同步"""
    r = await _run_job(sync_all_shops_questions, "WB questions")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_funnel():
    """WB 销售漏斗数据同步"""
    r = await _run_job(sync_all_shops_funnel, "WB funnel")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_returns():
    """WB 退货数据同步"""
    r = await _run_job(sync_all_shops_returns, "WB returns")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.hourly
@pytest.mark.asyncio
async def test_sync_all_shops_return_claims():
    """WB 买家退货申请同步"""
    r = await _run_job(sync_all_shops_return_claims, "WB return_claims")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.hourly
@pytest.mark.asyncio
async def test_sync_all_shops_chat_events():
    """WB 买家聊天事件同步"""
    r = await _run_job(sync_all_shops_chat_events, "WB chat_events")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_marketplace_orders():
    """WB Marketplace 订单同步"""
    r = await _run_job(sync_all_shops_marketplace_orders, "WB marketplace_orders")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_order_metadata():
    """WB FBS 订单元数据同步"""
    r = await _run_job(sync_all_shops_order_metadata, "WB order_metadata")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_fbs_supplies():
    """WB FBS供货单同步"""
    r = await _run_job(sync_all_shops_fbs_supplies, "WB fbs_supplies")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_feedback_pins():
    """WB 评价置顶及自动取消置顶记录同步"""
    r = await _run_job(sync_all_shops_feedback_pins, "WB feedback_pins")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_reshipment_orders():
    """WB 重新发货订单状态快照同步"""
    r = await _run_job(
        sync_all_shops_reshipment_orders,
        "WB reshipment_orders",
    )
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_balance():
    """WB 余额同步"""
    r = await _run_job(sync_all_shops_balance, "WB balance")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_seller_balance():
    """WB 财务域卖家余额同步"""
    r = await _run_job(sync_all_shops_seller_balance, "WB seller balance")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_sales_report_list():
    """WB 上一自然周财务报表列表同步"""
    r = await _run_job(sync_all_shops_sales_report_list, "WB sales report list")
    assert r["status"] in ("success", "skipped")
    assert all(
        shop_result["status"] == "success"
        for shop_result in r.get("results", {}).values()
    )


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_region_sales():
    """WB 区域销售报告同步"""
    r = await _run_job(sync_all_shops_region_sales, "WB region sales")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_product_search_texts():
    """WB 商品搜索词报告同步"""
    r = await _run_job(sync_all_shops_product_search_texts, "WB product search texts")
    assert r["status"] in ("success", "skipped")
    assert all(
        shop_result["status"] == "success"
        for shop_result in r.get("results", {}).values()
    )


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.asyncio
async def test_sync_all_shops_search_traffic():
    """WB 搜索流量报告同步"""
    r = await _run_job(sync_all_shops_search_traffic, "WB search traffic")
    assert r["status"] in ("success", "skipped")
    assert all(
        shop_result["status"] == "success"
        for shop_result in r.get("results", {}).values()
    )


# ───────────────────────────────────────────────
# Wildberries 小时级同步任务
# ───────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.hourly
@pytest.mark.asyncio
async def test_sync_all_shops_advert_stats_hourly():
    """WB 广告统计小时同步"""
    r = await _run_job(sync_all_shops_advert_stats_hourly, "WB advert_stats_hourly")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.wb
@pytest.mark.hourly
@pytest.mark.asyncio
async def test_sync_all_shops_search_cluster_stat_hourly():
    """WB 搜索关键字小时同步"""
    r = await _run_job(
        sync_all_shops_search_cluster_stat_hourly, "WB search_cluster_hourly"
    )
    assert r["status"] in ("success", "skipped")


# ───────────────────────────────────────────────
# Ozon 同步任务
# ───────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_postings():
    """Ozon 订单数据同步"""
    r = await _run_job(sync_all_shops_postings, "Ozon postings")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_returns():
    """Ozon 退货数据同步"""
    r = await _run_job(sync_all_shops_ozon_returns, "Ozon returns")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_reviews():
    """Ozon 评价数据同步"""
    r = await _run_job(sync_all_shops_reviews, "Ozon reviews")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_finance():
    """Ozon 财务数据同步"""
    r = await _run_job(sync_all_shops_ozon_finance, "Ozon finance")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_accrual_types():
    """Ozon 应计类型同步"""
    r = await _run_job(sync_all_shops_accrual_types, "Ozon accrual_types")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_products():
    """Ozon 商品信息同步（维度数据）"""
    r = await _run_job(sync_all_shops_ozon_products, "Ozon products")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_fbo_postings():
    """Ozon FBO 订单同步"""
    r = await _run_job(sync_all_shops_fbo_postings, "Ozon fbo_postings")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.advert
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_adverts():
    """Ozon 广告活动 + 日统计同步（Performance API，秒级）"""
    r = await _run_job(sync_all_shops_ozon_adverts, "Ozon adverts")
    assert r["status"] in ("success", "skipped")


@pytest.mark.integration
@pytest.mark.ozon
@pytest.mark.advert
@pytest.mark.asyncio
async def test_sync_all_shops_ozon_advert_products():
    """Ozon 广告 SKU 明细同步（异步报表，耗时数分钟）"""
    r = await _run_job(sync_all_shops_ozon_advert_products, "Ozon advert_products")
    assert r["status"] in ("success", "skipped")
