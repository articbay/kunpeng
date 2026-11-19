"""Ozon DWD CRUD operations."""

from .advert_efficiency import (
    CRUDDWDOzonAdvertEfficiencyDetail,
    crud_dwd_ozon_advert_efficiency_detail,
)
from .customer_voice import (
    CRUDDWDOzonCustomerVoiceDetail,
    crud_dwd_ozon_customer_voice_detail,
)
from .order_detail import CRUDDWDOzonOrderDetail, crud_dwd_ozon_order_detail
from .product_name_translation import (
    CRUDDWDOzonProductNameTranslation,
    crud_dwd_ozon_product_name_translation,
)
from .return_detail import CRUDDWDOzonReturnDetail, crud_dwd_ozon_return_detail
from .sales_funnel import (
    CRUDDWDOzonSalesFunnelDetail,
    crud_dwd_ozon_sales_funnel_detail,
)

__all__ = [
    "CRUDDWDOzonAdvertEfficiencyDetail",
    "CRUDDWDOzonCustomerVoiceDetail",
    "CRUDDWDOzonOrderDetail",
    "CRUDDWDOzonProductNameTranslation",
    "CRUDDWDOzonReturnDetail",
    "CRUDDWDOzonSalesFunnelDetail",
    "crud_dwd_ozon_order_detail",
    "crud_dwd_ozon_product_name_translation",
    "crud_dwd_ozon_return_detail",
    "crud_dwd_ozon_customer_voice_detail",
    "crud_dwd_ozon_advert_efficiency_detail",
    "crud_dwd_ozon_sales_funnel_detail",
]
