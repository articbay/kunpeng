"""DWD 层 CRUD。"""

from kunpeng.crud.dwd.ozon import crud_dwd_ozon_return_detail
from kunpeng.crud.dwd.wildberries import (
    crud_dwd_wb_advert_activity_detail,
    crud_dwd_wb_advert_bid_config,
    crud_dwd_wb_advert_stats_daily_incr,
    crud_dwd_wb_advert_stats_hourly_incr,
    crud_dwd_wb_order_detail,
    crud_dwd_wb_order_statistics_detail,
    crud_dwd_wb_return_detail,
    crud_dwd_wb_sales_funnel_detail,
    crud_dwd_wb_sales_report_detail,
    crud_dwd_wb_sales_report_summary,
    crud_dwd_wb_voc_feedback_detail,
    crud_dwd_wb_voc_question_detail,
)

__all__ = [
    "crud_dwd_ozon_return_detail",
    "crud_dwd_wb_advert_activity_detail",
    "crud_dwd_wb_advert_bid_config",
    "crud_dwd_wb_advert_stats_hourly_incr",
    "crud_dwd_wb_advert_stats_daily_incr",
    "crud_dwd_wb_sales_report_detail",
    "crud_dwd_wb_sales_funnel_detail",
    "crud_dwd_wb_sales_report_summary",
    "crud_dwd_wb_order_detail",
    "crud_dwd_wb_order_statistics_detail",
    "crud_dwd_wb_return_detail",
    "crud_dwd_wb_voc_feedback_detail",
    "crud_dwd_wb_voc_question_detail",
]
"""
DWD 层 CRUD 模块
"""
from kunpeng.crud.dwd.wildberries.adverts_report import crud_dwd_wb_adverts_report_detail

__all__ = [
    "crud_dwd_wb_adverts_report_detail",
]
