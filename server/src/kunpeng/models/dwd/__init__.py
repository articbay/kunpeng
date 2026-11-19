"""DWD 层数据模型。"""

from kunpeng.models.dwd.ozon import (
    DWDOzonAdvertEfficiencyDetail,
    DWDOzonCustomerVoiceDetail,
    DWDOzonOrderDetail,
    DWDOzonProductNameTranslation,
    DWDOzonReturnDetail,
    DWDOzonSalesFunnelDetail,
)
from kunpeng.models.dwd.wildberries import (
    DWDWBAdvertActivityDetail,
    DWDWBAdvertBidConfig,
    DWDWBAdvertStatsDailyIncr,
    DWDWBAdvertStatsHourlyIncr,
    DWDWBOrderDetail,
    DWDWBOrderStatisticsDetail,
    DWDWBReturnDetail,
    DWDWBSalesFunnelDetail,
    DWDWBSalesReportDetail,
    DWDWBSalesReportSummary,
    DWDWBVOCFeedbackDetail,
    DWDWBVOCQuestionDetail,
)

__all__ = [
    "DWDOzonAdvertEfficiencyDetail",
    "DWDOzonCustomerVoiceDetail",
    "DWDOzonOrderDetail",
    "DWDOzonProductNameTranslation",
    "DWDOzonReturnDetail",
    "DWDOzonSalesFunnelDetail",
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
DWD 层模型
"""
from kunpeng.models.dwd.wildberries.adverts_report import DWDWBAdvertsReportDetail

__all__.append("DWDWBAdvertsReportDetail")
