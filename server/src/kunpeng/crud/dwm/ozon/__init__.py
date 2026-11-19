"""Ozon DWM CRUD operations."""

from .goods_trade_return_day import (
    CRUDDWMOzonGoodsTradeReturnDay,
    crud_dwm_ozon_goods_trade_return_day,
)
from .order_lifecycle_detail import (
    CRUDDWMOzonOrderLifecycleDetail,
    crud_dwm_ozon_order_lifecycle_detail,
)
from .refresh_scope import CRUDDWMOzonRefreshScope, crud_dwm_ozon_refresh_scope

__all__ = [
    "CRUDDWMOzonGoodsTradeReturnDay",
    "CRUDDWMOzonOrderLifecycleDetail",
    "crud_dwm_ozon_goods_trade_return_day",
    "crud_dwm_ozon_order_lifecycle_detail",
    "CRUDDWMOzonRefreshScope",
    "crud_dwm_ozon_refresh_scope",
]
