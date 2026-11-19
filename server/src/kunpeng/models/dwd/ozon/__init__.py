"""Ozon DWD models."""

from .advert_efficiency import DWDOzonAdvertEfficiencyDetail
from .customer_voice import DWDOzonCustomerVoiceDetail
from .order_detail import DWDOzonOrderDetail
from .product_name_translation import DWDOzonProductNameTranslation
from .return_detail import DWDOzonReturnDetail
from .sales_funnel import DWDOzonSalesFunnelDetail

__all__ = [
    "DWDOzonAdvertEfficiencyDetail",
    "DWDOzonCustomerVoiceDetail",
    "DWDOzonOrderDetail",
    "DWDOzonProductNameTranslation",
    "DWDOzonReturnDetail",
    "DWDOzonSalesFunnelDetail",
]
