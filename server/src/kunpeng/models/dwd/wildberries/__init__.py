"""Wildberries DWD 数据模型。"""

from .advert import (
    DWDWBAdvertActivityDetail,
    DWDWBAdvertBidConfig,
    DWDWBAdvertStatsDailyIncr,
    DWDWBAdvertStatsHourlyIncr,
)
from .finance import DWDWBSalesReportDetail
from .funnel import DWDWBSalesFunnelDetail
from .order_detail import DWDWBOrderDetail
from .order_statistics_detail import DWDWBOrderStatisticsDetail
from .return_detail import DWDWBReturnDetail
from .sales_report_summary import DWDWBSalesReportSummary
from .voc_feedback import DWDWBVOCFeedbackDetail
from .voc_question import DWDWBVOCQuestionDetail

__all__ = [
    "DWDWBAdvertActivityDetail",
    "DWDWBAdvertBidConfig",
    "DWDWBAdvertStatsHourlyIncr",
    "DWDWBAdvertStatsDailyIncr",
    "DWDWBSalesReportDetail",
    "DWDWBSalesFunnelDetail",
    "DWDWBSalesReportSummary",
    "DWDWBOrderDetail",
    "DWDWBOrderStatisticsDetail",
    "DWDWBReturnDetail",
    "DWDWBVOCFeedbackDetail",
    "DWDWBVOCQuestionDetail",
]
"""
Wildberries DWD 层模型
"""
from kunpeng.models.dwd.wildberries.adverts_report import DWDWBAdvertsReportDetail

__all__ = [
    "DWDWBAdvertsReportDetail",
]
