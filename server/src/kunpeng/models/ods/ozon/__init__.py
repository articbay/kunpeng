"""
Ozon ODS 层模型
"""
# 财务应计类型字典
from kunpeng.models.ods.ozon.accrual_types import ODSOzonFinanceAccrualType
from kunpeng.models.ods.ozon.analytics import (
    ODSOzonAnalyticsDataDaily,
    ODSOzonAnalyticsTotalsWindow,
)

# 订单相关表
from kunpeng.models.ods.ozon.postings import (
    ODSOzonFBSPosting,
    ODSOzonFBSPostingProduct,
    ODSOzonFBSPostingDelivery,
    ODSOzonFBSPostingCancellation,
    ODSOzonFBSPostingOptional,
    ODSOzonFBSPostingExternal,
)

# FBO订单相关表
from kunpeng.models.ods.ozon.fbo_postings import (
    ODSOzonFBOPosting,
    ODSOzonFBOPostingProduct,
)
from kunpeng.models.ods.ozon.posting_reports import (
    ODSOzonPostingReportRow,
    ODSOzonPostingReportTask,
)

# 待处理（未发货）FBS 订单表（新订单数据源）
from kunpeng.models.ods.ozon.unfulfilled_postings import ODSOzonUnfulfilledPosting

# 退货相关表
from kunpeng.models.ods.ozon.returns import (
    ODSOzonReturn,
    ODSOzonReturnProduct,
    ODSOzonReturnStorage,
)

# 评价表
from kunpeng.models.ods.ozon.reviews import ODSOzonReview
from kunpeng.models.ods.ozon.customer_engagement import (
    ODSOzonChat,
    ODSOzonChatMessage,
    ODSOzonQuestion,
    ODSOzonQuestionAnswer,
    ODSOzonReviewComment,
)
from kunpeng.models.ods.ozon.status_history import (
    ODSOzonPostingStatusHistory,
    ODSOzonReturnStatusHistory,
)

# 商品表
from kunpeng.models.ods.ozon.products import ODSOzonProduct

# 广告相关表
from kunpeng.models.ods.ozon.adverts import (
    ODSOzonAdvCampaign,
    ODSOzonAdvStatDaily,
    ODSOzonAdvStatProductDaily,
)
from kunpeng.models.ods.ozon.advert_stats_hourly import ODSOzonAdvStatProductHourly

# 财务应计相关表
from kunpeng.models.ods.ozon.finance import (
    ODSOzonFinanceAccrual,
    ODSOzonAccrualFee,
)

# 销售实现报告相关表
from kunpeng.models.ods.ozon.realization import (
    ODSOzonFinanceRealizationHeader,
    ODSOzonFinanceRealizationRow,
)

__all__ = [
    # 财务应计类型字典
    "ODSOzonFinanceAccrualType",
    # 经营分析
    "ODSOzonAnalyticsDataDaily",
    "ODSOzonAnalyticsTotalsWindow",
    # 订单相关表
    "ODSOzonFBSPosting",
    "ODSOzonFBSPostingProduct",
    "ODSOzonFBSPostingDelivery",
    "ODSOzonFBSPostingCancellation",
    "ODSOzonFBSPostingOptional",
    "ODSOzonFBSPostingExternal",
    # FBO订单相关表
    "ODSOzonFBOPosting",
    "ODSOzonFBOPostingProduct",
    "ODSOzonPostingReportTask",
    "ODSOzonPostingReportRow",
    # 待处理（未发货）FBS 订单表（新订单）
    "ODSOzonUnfulfilledPosting",
    # 退货相关表
    "ODSOzonReturn",
    "ODSOzonReturnProduct",
    "ODSOzonReturnStorage",
    # 评价表
    "ODSOzonReview",
    "ODSOzonReviewComment",
    "ODSOzonQuestion",
    "ODSOzonQuestionAnswer",
    "ODSOzonChat",
    "ODSOzonChatMessage",
    "ODSOzonPostingStatusHistory",
    "ODSOzonReturnStatusHistory",
    # 商品表
    "ODSOzonProduct",
    # 广告相关表
    "ODSOzonAdvCampaign",
    "ODSOzonAdvStatDaily",
    "ODSOzonAdvStatProductDaily",
    "ODSOzonAdvStatProductHourly",
    # 财务应计相关表
    "ODSOzonFinanceAccrual",
    "ODSOzonAccrualFee",
    # 销售实现报告相关表
    "ODSOzonFinanceRealizationHeader",
    "ODSOzonFinanceRealizationRow",
]
