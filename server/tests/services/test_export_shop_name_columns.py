"""Guard the shared shop ID/name column convention for data exports."""

import pytest

from kunpeng.services.ozon_advert_efficiency_service import (
    OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS,
)
from kunpeng.services.ozon_customer_voice_service import (
    OZON_CUSTOMER_VOICE_EXPORT_COLUMNS,
)
from kunpeng.services.ozon_goods_daily_analysis_service import (
    EXPORT_COLUMNS as OZON_GOODS_DAILY_COLUMNS,
)
from kunpeng.services.ozon_order_lifecycle_service import (
    EXPORT_COLUMNS as OZON_ORDER_LIFECYCLE_COLUMNS,
)
from kunpeng.services.ozon_order_service import (
    ORDER_EXPORT_COLUMNS as OZON_ORDER_COLUMNS,
)
from kunpeng.services.ozon_return_service import OZON_RETURN_EXPORT_COLUMNS
from kunpeng.services.ozon_sales_funnel_service import (
    OZON_SALES_FUNNEL_EXPORT_COLUMNS,
)
from kunpeng.services.wb_financial_report_service import FINANCIAL_REPORT_COLUMNS
from kunpeng.services.wb_goods_daily_analysis_service import (
    EXPORT_COLUMNS as WB_GOODS_DAILY_COLUMNS,
)
from kunpeng.services.wb_order_lifecycle_service import (
    EXPORT_COLUMNS as WB_ORDER_LIFECYCLE_COLUMNS,
)
from kunpeng.services.wb_order_service import ORDER_EXPORT_COLUMNS as WB_ORDER_COLUMNS
from kunpeng.services.wb_order_statistics_service import (
    ORDER_STATISTICS_EXPORT_COLUMNS,
)
from kunpeng.services.wb_return_service import RETURN_EXPORT_COLUMNS
from kunpeng.services.wb_sales_funnel_detail_service import (
    SALES_FUNNEL_DETAIL_COLUMNS,
)
from kunpeng.services.wb_sales_report_summary_service import (
    SALES_REPORT_SUMMARY_COLUMNS,
)
from kunpeng.services.wb_voc_feedback_service import FEEDBACK_EXPORT_COLUMNS
from kunpeng.services.wb_voc_question_service import QUESTION_EXPORT_COLUMNS


@pytest.mark.parametrize(
    "columns",
    [
        OZON_GOODS_DAILY_COLUMNS,
        OZON_ORDER_LIFECYCLE_COLUMNS,
        OZON_SALES_FUNNEL_EXPORT_COLUMNS,
        OZON_ADVERT_EFFICIENCY_EXPORT_COLUMNS,
        OZON_CUSTOMER_VOICE_EXPORT_COLUMNS,
        OZON_ORDER_COLUMNS,
        OZON_RETURN_EXPORT_COLUMNS,
        WB_GOODS_DAILY_COLUMNS,
        WB_ORDER_LIFECYCLE_COLUMNS,
        WB_ORDER_COLUMNS,
        ORDER_STATISTICS_EXPORT_COLUMNS,
        RETURN_EXPORT_COLUMNS,
        FEEDBACK_EXPORT_COLUMNS,
        QUESTION_EXPORT_COLUMNS,
        FINANCIAL_REPORT_COLUMNS,
        SALES_REPORT_SUMMARY_COLUMNS,
        SALES_FUNNEL_DETAIL_COLUMNS,
    ],
)
def test_shop_name_immediately_follows_shop_id(columns):
    fields = [field for _, field in columns]
    shop_id_index = fields.index("shop_id")
    assert fields[shop_id_index + 1] == "shop_name"
