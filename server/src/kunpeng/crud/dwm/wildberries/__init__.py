"""Wildberries DWM CRUD operations."""

from .goods_oper_day import CRUDDWMWBGoodsOperDay, crud_dwm_wb_goods_oper_day
from .goods_daily_analysis import (
    CRUDDWMWBGoodsDailyAnalysis,
    crud_dwm_wb_goods_daily_analysis,
)
from .order_lifecycle_detail import (
    CRUDDWMWBOrderLifecycleDetail,
    crud_dwm_wb_order_lifecycle_detail,
)
from .order_lifecycle_query import (
    CRUDDWMWBOrderLifecycleQuery,
    crud_dwm_wb_order_lifecycle_query,
)

__all__ = [
    "CRUDDWMWBGoodsDailyAnalysis",
    "CRUDDWMWBGoodsOperDay",
    "CRUDDWMWBOrderLifecycleDetail",
    "CRUDDWMWBOrderLifecycleQuery",
    "crud_dwm_wb_goods_daily_analysis",
    "crud_dwm_wb_goods_oper_day",
    "crud_dwm_wb_order_lifecycle_detail",
    "crud_dwm_wb_order_lifecycle_query",
]
