"""DWM layer CRUD operations."""

from kunpeng.crud.dwm.ozon import (
    crud_dwm_ozon_goods_trade_return_day,
    crud_dwm_ozon_order_lifecycle_detail,
)
from kunpeng.crud.dwm.wildberries import (
    crud_dwm_wb_goods_oper_day,
    crud_dwm_wb_order_lifecycle_detail,
)

__all__ = [
    "crud_dwm_ozon_goods_trade_return_day",
    "crud_dwm_ozon_order_lifecycle_detail",
    "crud_dwm_wb_goods_oper_day",
    "crud_dwm_wb_order_lifecycle_detail",
]
