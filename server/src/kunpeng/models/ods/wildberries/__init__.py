"""Wildberries ODS 数据模型。"""

from .adv_enhanced import (
    ODSWBAdvertFullStat,
    ODSWBAdvertV2,
    ODSWBBidRecommendation,
    ODSWBNormQueryBid,
    ODSWBNormQueryList,
    ODSWBNormQueryMinus,
    ODSWBNormQueryStat,
    ODSWBPromotionCount,
)
from .advert_stats_hourly import ODSWBAdvertStatHourly
from .adverts import ODSWBAdvert, ODSWBAdvertStat
from .balance import (
    ODSWBAdvertBudget,
    ODSWBAdvertProduct,
    ODSWBBalance,
    ODSWBCashback,
    ODSWBSearchClusterStat,
)
from .chat_events import ODSWBChatEvent
from .feedback_pins import ODSWBFeedbackPin
from .feedbacks import ODSWBFeedback, ODSWBQuestion
from .finance import ODSWBSalesReport
from .finance_daily import ODSWBSalesReportDaily
from .funnel import ODSWBSalesFunnel
from .marketplace import ODSWBMarketplaceOrder, ODSWBMarketplaceOrderStatusHistory
from .new_orders import ODSWBNewOrder
from .order_metadata import ODSWBOrderMetadata
from .product_search_text import ODSWBProductSearchText
from .region_sale import ODSWBRegionSale
from .reshipment_orders import ODSWBReshipmentOrder
from .return_claims import ODSWBReturnClaim
from .returns import ODSWBGoodsReturn
from .sales import ODSWBSupplierOrder, ODSWBSupplierSale
from .sales_report_list import ODSWBSalesReportList
from .search_cluster_stat_hourly import ODSWBSearchClusterStatHourly
from .search_traffic import ODSWBSearchTraffic
from .seller_balance import ODSWBSellerBalance
from .supplies import ODSWBFbsSupply

__all__ = [
    "ODSWBSupplierSale",
    "ODSWBSupplierOrder",
    "ODSWBSalesFunnel",
    "ODSWBGoodsReturn",
    "ODSWBReturnClaim",
    "ODSWBChatEvent",
    "ODSWBFeedbackPin",
    "ODSWBAdvert",
    "ODSWBAdvertStat",
    "ODSWBAdvertStatHourly",
    "ODSWBFeedback",
    "ODSWBQuestion",
    "ODSWBSalesReport",
    "ODSWBSalesReportDaily",
    "ODSWBSalesReportList",
    "ODSWBMarketplaceOrder",
    "ODSWBMarketplaceOrderStatusHistory",
    "ODSWBOrderMetadata",
    "ODSWBBalance",
    "ODSWBCashback",
    "ODSWBAdvertProduct",
    "ODSWBAdvertBudget",
    "ODSWBSearchClusterStat",
    "ODSWBSearchClusterStatHourly",
    "ODSWBNewOrder",
    "ODSWBSellerBalance",
    "ODSWBRegionSale",
    "ODSWBProductSearchText",
    "ODSWBSearchTraffic",
    "ODSWBFbsSupply",
    "ODSWBReshipmentOrder",
    "ODSWBNormQueryBid",
    "ODSWBNormQueryMinus",
    "ODSWBNormQueryList",
    "ODSWBNormQueryStat",
    "ODSWBPromotionCount",
    "ODSWBBidRecommendation",
    "ODSWBAdvertFullStat",
    "ODSWBAdvertV2",
]
