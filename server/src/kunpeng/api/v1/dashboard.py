"""
仪表盘 API 路由（只读）

提供聚合总览接口，前端一次拉取即可渲染全部图表：
全局 KPI、按日趋势（分平台）、平台维度、店铺维度、热销商品 Top。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_user, get_db
from kunpeng.models.user import User
from kunpeng.schemas.dashboard import DashboardSummary
from kunpeng.services.dashboard_service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数（含今天）"),
    platform: Optional[str] = Query(
        None, description="平台过滤：wildberries / ozon，留空为全部"
    ),
    shop_id: Optional[int] = Query(None, description="店铺过滤，留空为全部"),
    top_limit: int = Query(10, ge=1, le=50, description="热销商品数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    """获取仪表盘总览数据（当前用户名下店铺）"""
    service = DashboardService(db)
    return await service.get_summary(
        user_id=current_user.id,
        days=days,
        platform=platform,
        shop_id=shop_id,
        top_limit=top_limit,
    )
