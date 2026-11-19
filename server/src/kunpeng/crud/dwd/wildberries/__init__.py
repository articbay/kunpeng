"""Wildberries DWD CRUD。"""

from .advert import (
    crud_dwd_wb_advert_activity_detail,
    crud_dwd_wb_advert_bid_config,
    crud_dwd_wb_advert_stats_daily_incr,
    crud_dwd_wb_advert_stats_hourly_incr,
)
from .finance import crud_dwd_wb_sales_report_detail
from .funnel import crud_dwd_wb_sales_funnel_detail
from .order_detail import CRUDDWDWBOrderDetail, crud_dwd_wb_order_detail
from .order_statistics_detail import (
    CRUDDWDWBOrderStatisticsDetail,
    crud_dwd_wb_order_statistics_detail,
)
from .return_detail import CRUDDWDWBReturnDetail, crud_dwd_wb_return_detail
from .sales_report_summary import crud_dwd_wb_sales_report_summary
from .voc_feedback import CRUDDWDWBVOCFeedbackDetail, crud_dwd_wb_voc_feedback_detail
from .voc_question import CRUDDWDWBVOCQuestionDetail, crud_dwd_wb_voc_question_detail

__all__ = [
    "crud_dwd_wb_advert_activity_detail",
    "crud_dwd_wb_advert_bid_config",
    "crud_dwd_wb_advert_stats_hourly_incr",
    "crud_dwd_wb_advert_stats_daily_incr",
    "crud_dwd_wb_sales_report_detail",
    "crud_dwd_wb_sales_funnel_detail",
    "crud_dwd_wb_sales_report_summary",
    "CRUDDWDWBOrderDetail",
    "crud_dwd_wb_order_detail",
    "CRUDDWDWBOrderStatisticsDetail",
    "crud_dwd_wb_order_statistics_detail",
    "CRUDDWDWBReturnDetail",
    "crud_dwd_wb_return_detail",
    "CRUDDWDWBVOCFeedbackDetail",
    "crud_dwd_wb_voc_feedback_detail",
    "CRUDDWDWBVOCQuestionDetail",
    "crud_dwd_wb_voc_question_detail",
]
"""
Wildberries DWD 层 CRUD 模块
"""
from kunpeng.crud.dwd.wildberries.adverts_report import crud_dwd_wb_adverts_report_detail

__all__ = [
    "crud_dwd_wb_adverts_report_detail",
]
