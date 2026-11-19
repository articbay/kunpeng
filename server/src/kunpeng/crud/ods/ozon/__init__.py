"""
Ozon ODS 层 CRUD
"""
# 财务应计类型
from kunpeng.crud.ods.ozon.accrual_types import crud_ods_ozon_accrual_types
from kunpeng.crud.ods.ozon.analytics import (
    crud_ods_ozon_analytics_data_daily,
    crud_ods_ozon_analytics_totals_window,
)

# 订单相关
from kunpeng.crud.ods.ozon.postings import (
    crud_ods_ozon_fbs_posting,
    crud_ods_ozon_fbs_posting_product,
    crud_ods_ozon_fbs_posting_delivery,
    crud_ods_ozon_fbs_posting_cancellation,
    crud_ods_ozon_fbs_posting_optional,
    crud_ods_ozon_fbs_posting_external,
)

# FBO订单相关
from kunpeng.crud.ods.ozon.fbo_postings import (
    crud_ods_ozon_fbo_posting,
    crud_ods_ozon_fbo_posting_product,
)
from kunpeng.crud.ods.ozon.posting_reports import (
    crud_ods_ozon_posting_report_row,
    crud_ods_ozon_posting_report_task,
)

# 待处理（未发货）FBS 订单（新订单数据源）
from kunpeng.crud.ods.ozon.unfulfilled_postings import (
    crud_ods_ozon_unfulfilled_posting,
)

# 退货相关
from kunpeng.crud.ods.ozon.returns import (
    crud_ods_ozon_return,
    crud_ods_ozon_return_product,
    crud_ods_ozon_return_storage,
)

# 评价
from kunpeng.crud.ods.ozon.reviews import crud_ods_ozon_review
from kunpeng.crud.ods.ozon.customer_engagement import (
    crud_ods_ozon_chat,
    crud_ods_ozon_chat_message,
    crud_ods_ozon_question,
    crud_ods_ozon_question_answer,
    crud_ods_ozon_review_comment,
)
from kunpeng.crud.ods.ozon.status_history import (
    crud_ods_ozon_posting_status_history,
    crud_ods_ozon_return_status_history,
)

# 商品
from kunpeng.crud.ods.ozon.products import crud_ods_ozon_product

# 广告相关
from kunpeng.crud.ods.ozon.adverts import (
    crud_ods_ozon_adv_campaign,
    crud_ods_ozon_adv_stat_daily,
    crud_ods_ozon_adv_stat_product_daily,
)
from kunpeng.crud.ods.ozon.advert_stats_hourly import crud_ods_ozon_adv_stat_product_hourly

# 财务应计相关
from kunpeng.crud.ods.ozon.finance import (
    crud_ods_ozon_finance_accrual,
    crud_ods_ozon_accrual_fee,
)

# 销售实现报告相关
from kunpeng.crud.ods.ozon.realization import (
    crud_ods_ozon_finance_realization_header,
    crud_ods_ozon_finance_realization_row,
)

__all__ = [
    # 财务应计类型
    "crud_ods_ozon_accrual_types",
    # 经营分析
    "crud_ods_ozon_analytics_data_daily",
    "crud_ods_ozon_analytics_totals_window",
    # 订单相关
    "crud_ods_ozon_fbs_posting",
    "crud_ods_ozon_fbs_posting_product",
    "crud_ods_ozon_fbs_posting_delivery",
    "crud_ods_ozon_fbs_posting_cancellation",
    "crud_ods_ozon_fbs_posting_optional",
    "crud_ods_ozon_fbs_posting_external",
    # FBO订单相关
    "crud_ods_ozon_fbo_posting",
    "crud_ods_ozon_fbo_posting_product",
    "crud_ods_ozon_posting_report_task",
    "crud_ods_ozon_posting_report_row",
    # 待处理（未发货）FBS 订单（新订单）
    "crud_ods_ozon_unfulfilled_posting",
    # 退货相关
    "crud_ods_ozon_return",
    "crud_ods_ozon_return_product",
    "crud_ods_ozon_return_storage",
    # 评价
    "crud_ods_ozon_review",
    "crud_ods_ozon_review_comment",
    "crud_ods_ozon_question",
    "crud_ods_ozon_question_answer",
    "crud_ods_ozon_chat",
    "crud_ods_ozon_chat_message",
    "crud_ods_ozon_posting_status_history",
    "crud_ods_ozon_return_status_history",
    # 商品
    "crud_ods_ozon_product",
    # 广告相关
    "crud_ods_ozon_adv_campaign",
    "crud_ods_ozon_adv_stat_daily",
    "crud_ods_ozon_adv_stat_product_daily",
    "crud_ods_ozon_adv_stat_product_hourly",
    # 财务应计相关
    "crud_ods_ozon_finance_accrual",
    "crud_ods_ozon_accrual_fee",
    # 销售实现报告相关
    "crud_ods_ozon_finance_realization_header",
    "crud_ods_ozon_finance_realization_row",
]
