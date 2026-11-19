"""
Wildberries API 路由（简化版 - ODS 层）
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db

logger = logging.getLogger(__name__)
from kunpeng.crud import shop_crud
from kunpeng.models.user import User
from kunpeng.schemas.common import MessageResponse, PageResponse
from kunpeng.schemas.wildberries import (
    WBFinancialReportDetailItem,
    WBSalesFunnelDetailItem,
    WBSalesFunnelListItem,
    WBSalesReportSummaryItem,
    WBSyncRequest,
    WBSyncResponse,
)
from kunpeng.services.wb_dwd_service import wb_dwd_service
from kunpeng.services.wb_financial_report_service import wb_financial_report_service
from kunpeng.services.wb_sales_funnel_detail_service import (
    wb_sales_funnel_detail_service,
)
from kunpeng.services.wb_sales_funnel_service import WBSalesFunnelService
from kunpeng.services.wb_sales_report_summary_service import (
    wb_sales_report_summary_service,
)
from kunpeng.services.wb_sync_service import WBSyncService
from kunpeng.utils.timezone import now_platform


async def _require_authenticated_reader_or_admin_writer(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通用户只有数据查看权限",
        )
    return current_user


router = APIRouter(
    tags=["wildberries"],
    dependencies=[Depends(_require_authenticated_reader_or_admin_writer)],
)


async def _ensure_shop_access(
    db: AsyncSession, *, current_user: User, shop_id: int
) -> None:
    if not await shop_crud.user_can_access(
        db, user_id=current_user.id, shop_id=shop_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在",
        )


async def _accessible_wb_shop_ids(db: AsyncSession, *, current_user: User) -> List[int]:
    return await shop_crud.get_accessible_ids_by_user_platform(
        db, user_id=current_user.id, platform="wildberries"
    )


def _excel_content_disposition(business_name: str, fallback_name: str) -> str:
    timestamp = now_platform().strftime("%Y%m%d_%H%M%S")
    filename = f"{business_name}_{timestamp}.xlsx"
    return (
        f'attachment; filename="{fallback_name}_{timestamp}.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


# ==================== 同步相关接口 ====================


@router.post("/sync", response_model=WBSyncResponse)
async def sync_wildberries_data(
    sync_req: WBSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    手动触发 Wildberries 数据同步（临时关闭鉴权）
    """
    logger.debug(f"[API] 收到同步请求 - shop_id: {sync_req.shop_id}")
    # 获取店铺
    shop = await shop_crud.get(db, id=sync_req.shop_id)
    if not shop:
        logger.debug(f"[API] 店铺不存在: {sync_req.shop_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在",
        )

    # 执行同步
    logger.debug(f"[API] 开始执行同步 - shop_id: {sync_req.shop_id}")
    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_all(
        date_from=sync_req.date_from,
        date_to=sync_req.date_to,
        sync_types=sync_req.sync_types,
    )
    logger.debug(f"[API] 同步执行完成 - result: {result}")

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "同步失败"),
        )

    # 统计同步数量
    synced_count = {}
    for sync_type, sync_result in result.get("results", {}).items():
        if sync_result.get("status") == "success":
            synced_count[sync_type] = sync_result.get("count", 0)

    response = WBSyncResponse(
        status="success",
        message="数据同步完成",
        synced_count=synced_count,
    )
    logger.debug(f"[API] 返回同步响应: {response}")
    return response


@router.post("/sync/sales", response_model=MessageResponse)
async def sync_sales_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步销售数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_sales(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/orders", response_model=MessageResponse)
async def sync_orders_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步订单数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_orders(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/funnel", response_model=MessageResponse)
async def sync_funnel_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步销售漏斗数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    if date_from is None and date_to is None:
        result = await sync_service.sync_funnel_lookback()
    else:
        result = await sync_service.sync_funnel(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"], data=result)


@router.post("/sync/returns", response_model=MessageResponse)
async def sync_returns_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步退货数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_returns(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/marketplace-orders", response_model=MessageResponse)
async def sync_marketplace_orders_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步 Marketplace 订单数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_marketplace_orders(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/finance", response_model=MessageResponse)
async def sync_finance_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步财务数据（新销售报告API）"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_finance(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/finance-daily", response_model=MessageResponse)
async def sync_finance_daily_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步 WB 按日财务明细。"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_finance_daily(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/dwd/sales-report-detail")
async def sync_sales_report_dwd_only(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """独立手动触发指定店铺的财务结算明细 DWD 同步。"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    if shop.platform != "wildberries":
        raise HTTPException(status_code=400, detail="该店铺不是 Wildberries 店铺")

    try:
        stats = await wb_dwd_service.sync_sales_report_detail(
            db,
            shop_id=shop_id,
        )
    except Exception as exc:
        logger.error(f"[API] 店铺 {shop_id} 的 DWD 财务结算明细同步失败: {exc}")
        raise HTTPException(status_code=500, detail=f"DWD 同步失败: {exc}")

    return {
        "status": "success",
        "shop_id": shop_id,
        **stats,
    }


@router.post("/sync/dwd/sales-funnel-detail")
async def sync_sales_funnel_dwd_only(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """独立手动触发指定店铺的销售漏斗 DWD 同步。"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    if shop.platform != "wildberries":
        raise HTTPException(status_code=400, detail="该店铺不是 Wildberries 店铺")

    try:
        stats = await wb_dwd_service.sync_sales_funnel_detail(
            db,
            shop_id=shop_id,
        )
    except Exception as exc:
        logger.error(f"[API] 店铺 {shop_id} 的销售漏斗 DWD 同步失败: {exc}")
        raise HTTPException(status_code=500, detail=f"DWD 同步失败: {exc}")

    return {
        "status": "success",
        "shop_id": shop_id,
        **stats,
    }


@router.post("/sync/dwd/advert")
async def sync_advert_dwd_only(
    shop_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """从已有 ODS 手动构建指定店铺的四张广告 DWD 表。"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    if shop.platform != "wildberries":
        raise HTTPException(status_code=400, detail="该店铺不是 Wildberries 店铺")

    try:
        results = await wb_dwd_service.sync_advert_all(
            db,
            shop_id=shop_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[API] 店铺 %s 的广告 DWD 同步失败", shop_id)
        raise HTTPException(status_code=500, detail=f"DWD 同步失败: {exc}") from exc

    business_date = now_platform().date()
    return {
        "status": "success",
        "shop_id": shop_id,
        "date_from": (date_from or business_date).isoformat(),
        "date_to": (date_to or date_from or business_date).isoformat(),
        "results": results,
    }


@router.post("/sync/balance", response_model=MessageResponse)
async def sync_balance_only(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步余额和cashback数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_balance()

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/adverts", response_model=MessageResponse)
async def sync_adverts_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步广告数据（包含广告活动、广告商品、预算、搜索关键字统计）"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_adverts(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/adverts-hourly", response_model=MessageResponse)
async def sync_adverts_hourly(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """手动触发广告统计小时同步"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_advert_stats_hourly()

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/search-cluster-hourly", response_model=MessageResponse)
async def sync_search_cluster_hourly(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """手动触发搜索词统计小时同步"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_search_cluster_stat_hourly()

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


# ==================== 增强广告数据同步接口 ====================


def _build_adv_enhanced_response(result: Dict[str, Any]) -> WBSyncResponse:
    """保留增强广告各子任务结果，并生成可直接判断的汇总状态。"""
    normalized_results: Dict[str, Dict[str, Any]] = {}
    synced_count: Dict[str, int] = {}

    for sync_type, sync_result in result.get("results", {}).items():
        normalized_result = dict(sync_result)
        api_count = normalized_result.get("api_count")
        stored_count = normalized_result.get("count", 0)

        if (
            normalized_result.get("status") == "success"
            and api_count is not None
            and api_count > 0
            and stored_count == 0
        ):
            normalized_result["status"] = "error"
            normalized_result["message"] = (
                f"WB接口返回了 {api_count} 条数据，但没有数据成功入库"
            )

        normalized_results[sync_type] = normalized_result
        if normalized_result.get("status") == "success":
            synced_count[sync_type] = stored_count

    success_count = sum(
        item.get("status") == "success" for item in normalized_results.values()
    )
    error_count = len(normalized_results) - success_count

    if not normalized_results:
        response_status = result.get("status", "success")
        message = result.get("message", "增强广告数据同步未返回子任务结果")
    elif error_count == 0:
        response_status = "success"
        message = "增强广告数据同步完成"
    elif success_count == 0:
        response_status = "error"
        message = f"增强广告数据同步失败：{error_count}项失败"
    else:
        response_status = "partial_success"
        message = f"增强广告数据部分完成：{success_count}项成功，{error_count}项失败"

    return WBSyncResponse(
        status=response_status,
        message=message,
        synced_count=synced_count,
        results=normalized_results,
    )


@router.post("/sync/adv-enhanced", response_model=WBSyncResponse)
async def sync_adv_enhanced(
    sync_req: WBSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """同步所有增强广告数据(8个新API)"""
    logger.debug(f"[API] 收到增强广告数据同步请求 - shop_id: {sync_req.shop_id}")
    shop = await shop_crud.get(db, id=sync_req.shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_adv_enhanced(
        date_from=sync_req.date_from,
        date_to=sync_req.date_to,
    )

    response = _build_adv_enhanced_response(result)
    if response.status == "error":
        raise HTTPException(status_code=500, detail=response.model_dump())

    return response


@router.post("/sync/norm-query-bids", response_model=MessageResponse)
async def sync_norm_query_bids_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步标准查询竞价数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_norm_query_bids(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/norm-query-minus", response_model=MessageResponse)
async def sync_norm_query_minus_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步排除关键词数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_norm_query_minus(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/norm-query-list", response_model=MessageResponse)
async def sync_norm_query_list_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步标准查询列表数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_norm_query_list(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/norm-query-stats", response_model=MessageResponse)
async def sync_norm_query_stats_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步标准查询统计数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_norm_query_stats(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/promotion-count", response_model=MessageResponse)
async def sync_promotion_count_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步促销计数数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_promotion_count(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/bid-recommendations", response_model=MessageResponse)
async def sync_bid_recommendations_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步竞价推荐数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_bid_recommendations(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/advert-fullstats", response_model=MessageResponse)
async def sync_advert_fullstats_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步广告完整统计数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_advert_fullstats(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


@router.post("/sync/adverts-v2", response_model=MessageResponse)
async def sync_adverts_v2_only(
    shop_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅同步广告列表V2数据"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")

    sync_service = WBSyncService(db, shop)
    result = await sync_service.sync_adverts_v2(date_from, date_to)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return MessageResponse(message=result["message"])


# ==================== 数据查询接口 ====================
@router.get(
    "/financial-report-summaries",
    response_model=PageResponse[WBSalesReportSummaryItem],
)
async def list_financial_report_summaries(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    create_date_from: Optional[date] = None,
    create_date_to: Optional[date] = None,
    report_id: Optional[int] = Query(None, ge=1),
    seller_finance_name: Optional[str] = Query(None, max_length=255),
    report_type: Optional[int] = Query(None, ge=0),
    currency: Optional[str] = Query(None, max_length=10),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBSalesReportSummaryItem]:
    """分页查询指定店铺的 DWD 财务报告周汇总。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    if create_date_from and create_date_to and create_date_from > create_date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="create_date_from 不能晚于 create_date_to",
        )
    return await wb_sales_report_summary_service.list_summaries(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        create_date_from=create_date_from,
        create_date_to=create_date_to,
        report_id=report_id,
        seller_finance_name=seller_finance_name,
        report_type=report_type,
        currency=currency,
        page=page,
        page_size=page_size,
    )


@router.get("/financial-report-summaries/export")
async def export_financial_report_summaries(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    create_date_from: Optional[date] = None,
    create_date_to: Optional[date] = None,
    report_id: Optional[int] = Query(None, ge=1),
    seller_finance_name: Optional[str] = Query(None, max_length=255),
    report_type: Optional[int] = Query(None, ge=0),
    currency: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """按查询条件导出全部 DWD 财务报告周汇总。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    if create_date_from and create_date_to and create_date_from > create_date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="create_date_from 不能晚于 create_date_to",
        )
    content = await wb_sales_report_summary_service.export_summaries(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        create_date_from=create_date_from,
        create_date_to=create_date_to,
        report_id=report_id,
        seller_finance_name=seller_finance_name,
        report_type=report_type,
        currency=currency,
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": _excel_content_disposition(
                "WB财务报告周汇总",
                "wb_financial_summary",
            ),
        },
    )


@router.get(
    "/financial-report-details",
    response_model=PageResponse[WBFinancialReportDetailItem],
)
async def list_financial_report_details(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = Query(None, ge=1),
    vendor_code: Optional[str] = Query(None, max_length=255),
    rrd_id: Optional[int] = Query(None, ge=1),
    order_id: Optional[int] = Query(None, ge=1),
    seller_oper_name: Optional[str] = Query(None, max_length=255),
    doc_type_name: Optional[str] = Query(None, max_length=255),
    brand_name: Optional[str] = Query(None, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBFinancialReportDetailItem]:
    """分页查询指定店铺的财务报告周明细。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    return await wb_financial_report_service.list_report_details(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        rrd_id=rrd_id,
        order_id=order_id,
        seller_oper_name=seller_oper_name,
        doc_type_name=doc_type_name,
        brand_name=brand_name,
        page=page,
        page_size=page_size,
    )


@router.get("/financial-report-details/export")
async def export_financial_report_details(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = Query(None, ge=1),
    vendor_code: Optional[str] = Query(None, max_length=255),
    rrd_id: Optional[int] = Query(None, ge=1),
    order_id: Optional[int] = Query(None, ge=1),
    seller_oper_name: Optional[str] = Query(None, max_length=255),
    doc_type_name: Optional[str] = Query(None, max_length=255),
    brand_name: Optional[str] = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """按查询条件导出全部财务报告周明细。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    content = await wb_financial_report_service.export_report_details(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        rrd_id=rrd_id,
        order_id=order_id,
        seller_oper_name=seller_oper_name,
        doc_type_name=doc_type_name,
        brand_name=brand_name,
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": _excel_content_disposition(
                "WB财务报告周明细",
                "wb_financial_report",
            ),
        },
    )


@router.get(
    "/sales-funnel-details",
    response_model=PageResponse[WBSalesFunnelDetailItem],
)
async def list_sales_funnel_details(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = Query(None, ge=1),
    vendor_code: Optional[str] = Query(None, max_length=255),
    title: Optional[str] = Query(None, max_length=1000),
    subject_name: Optional[str] = Query(None, max_length=255),
    brand_name: Optional[str] = Query(None, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResponse[WBSalesFunnelDetailItem]:
    """分页查询指定店铺的 DWD 销售漏斗商品明细。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    return await wb_sales_funnel_detail_service.list_details(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        title=title,
        subject_name=subject_name,
        brand_name=brand_name,
        page=page,
        page_size=page_size,
    )


@router.get("/sales-funnel-details/export")
async def export_sales_funnel_details(
    shop_id: int = Query(..., ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = Query(None, ge=1),
    vendor_code: Optional[str] = Query(None, max_length=255),
    title: Optional[str] = Query(None, max_length=1000),
    subject_name: Optional[str] = Query(None, max_length=255),
    brand_name: Optional[str] = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """按查询条件导出全部 DWD 销售漏斗商品明细。"""
    await _ensure_shop_access(db, current_user=current_user, shop_id=shop_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from 不能晚于 date_to",
        )
    content = await wb_sales_funnel_detail_service.export_details(
        db,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        title=title,
        subject_name=subject_name,
        brand_name=brand_name,
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": _excel_content_disposition(
                "WB销售漏斗明细",
                "wb_sales_funnel",
            ),
        },
    )


@router.get("/sales-funnels", response_model=List[WBSalesFunnelListItem])
async def list_sales_funnels(
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = None,
    vendor_code: Optional[str] = None,
    brand_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[WBSalesFunnelListItem]:
    allowed_shop_ids = await _accessible_wb_shop_ids(db, current_user=current_user)
    sales_funnel_service = WBSalesFunnelService()
    return await sales_funnel_service.list_sales_funnels(
        db,
        shop_id=shop_id,
        allowed_shop_ids=allowed_shop_ids,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        brand_name=brand_name,
        subject_name=subject_name,
    )


@router.get("/sales-funnels/export")
async def export_sales_funnels(
    shop_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    nm_id: Optional[int] = None,
    vendor_code: Optional[str] = None,
    brand_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    allowed_shop_ids = await _accessible_wb_shop_ids(db, current_user=current_user)
    sales_funnel_service = WBSalesFunnelService()
    content = await sales_funnel_service.export_sales_funnels(
        db,
        shop_id=shop_id,
        allowed_shop_ids=allowed_shop_ids,
        date_from=date_from,
        date_to=date_to,
        nm_id=nm_id,
        vendor_code=vendor_code,
        brand_name=brand_name,
        subject_name=subject_name,
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": _excel_content_disposition(
                "WB销售漏斗",
                "wb_sales_funnels",
            ),
        },
    )


from fastapi import Query

from kunpeng.crud.dwd.wildberries.adverts_report import (
    crud_dwd_wb_adverts_report_detail,
)
from kunpeng.schemas.common import PageResponse
from kunpeng.schemas.wildberries import WBAdvertsReportDetailResponse


@router.get(
    "/adverts-report", response_model=PageResponse[WBAdvertsReportDetailResponse]
)
async def get_adverts_report(
    shop_id: Optional[int] = Query(None, description="店铺ID"),
    week: Optional[str] = Query(None, description="周度，如 week202530"),
    advert_id: Optional[int] = Query(None, description="广告ID"),
    advert_status: Optional[int] = Query(
        None, description="广告状态：0-已暂停，1-进行中"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """获取广告周度报表（分页查询）"""
    allowed_shop_ids = await _accessible_wb_shop_ids(db, current_user=current_user)
    items, total = await crud_dwd_wb_adverts_report_detail.get_paginated(
        db,
        shop_id=shop_id,
        allowed_shop_ids=allowed_shop_ids,
        week=week,
        advert_id=advert_id,
        advert_status=advert_status,
        page=page,
        page_size=page_size,
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/adverts-report/weeks")
async def get_available_weeks(
    shop_id: Optional[int] = Query(None, description="店铺ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """获取可用的周度列表"""
    allowed_shop_ids = await _accessible_wb_shop_ids(db, current_user=current_user)
    weeks = await crud_dwd_wb_adverts_report_detail.get_available_weeks(
        db, shop_id=shop_id, allowed_shop_ids=allowed_shop_ids
    )
    return {"weeks": weeks}


# ==================== Excel导出接口 ====================

import io

from fastapi.responses import StreamingResponse


@router.get("/adverts-report/export")
async def export_adverts_report_excel(
    shop_id: Optional[int] = Query(None, description="店铺ID"),
    week: Optional[str] = Query(None, description="周度，如 week202530"),
    advert_id: Optional[int] = Query(None, description="广告ID"),
    advert_status: Optional[int] = Query(
        None, description="广告状态：0-已暂停，1-进行中"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    导出广告周度报表为Excel

    Args:
        shop_id: 店铺ID过滤
        week: 周度过滤
        advert_id: 广告ID过滤
        advert_status: 广告状态过滤
    """
    # 惰性导入 openpyxl
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Excel导出功能需要安装 openpyxl: pip install openpyxl",
        )

    # 获取所有数据（不分页）
    allowed_shop_ids = await _accessible_wb_shop_ids(db, current_user=current_user)
    items, _ = await crud_dwd_wb_adverts_report_detail.get_paginated(
        db,
        shop_id=shop_id,
        allowed_shop_ids=allowed_shop_ids,
        week=week,
        advert_id=advert_id,
        advert_status=advert_status,
        page=1,
        page_size=10000,  # 足够大的数量
    )

    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "广告周度报表"

    # 表头样式
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="4472C4", end_color="4472C4", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 定义表头
    headers = [
        "店铺ID",
        "店铺名称",
        "周度",
        "广告ID",
        "广告名称",
        "广告状态",
        "付费曝光量",
        "付费点击量",
        "CTR (%)",
        "CPC (₽)",
        "加购次数",
        "订单次数",
        "CR (%)",
        "总花费 (₽)",
        "总销售金额 (₽)",
    ]

    # 写入表头
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 数据样式
    data_font = Font(name="微软雅黑", size=10)
    data_alignment = Alignment(horizontal="left", vertical="center")
    num_alignment = Alignment(horizontal="right", vertical="center")
    shop_names = await shop_crud.get_names_by_ids(db, shop_ids=allowed_shop_ids)

    # 写入数据
    for row_num, item in enumerate(items, 2):
        values = [
            (item.shop_id, True, None),
            (shop_names.get(item.shop_id, ""), False, None),
            (item.week, False, None),
            (item.advert_id, True, None),
            (item.advert_name or "", False, None),
            (item.advert_status_label or "", False, None),
            (item.paid_views or 0, True, None),
            (item.paid_clicks or 0, True, None),
            (item.ctr or 0, True, "0.00"),
            (item.cpc or 0, True, "0.00"),
            (item.atbs or 0, True, None),
            (item.orders or 0, True, None),
            (item.cr or 0, True, "0.00"),
            (item.sum_cost or 0, True, "0.00"),
            (item.sum_price or 0, True, "0.00"),
        ]
        for column, (value, numeric, number_format) in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=column, value=value)
            cell.font = data_font
            cell.alignment = num_alignment if numeric else data_alignment
            cell.border = thin_border
            if number_format:
                cell.number_format = number_format

    # 调整列宽
    widths = [10, 22, 15, 10, 30, 10, 12, 12, 10, 12, 10, 10, 10, 15, 18]
    for column, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(column)].width = width

    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # 返回文件响应
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": _excel_content_disposition(
                "WB广告周报",
                "wb_adverts_report",
            )
        },
    )
