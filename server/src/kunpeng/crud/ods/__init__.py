"""ODS 层 CRUD 模块。"""

from kunpeng.crud.ods.wildberries import (
    crud_ods_wb_advert,
    crud_ods_wb_advert_budget,
    crud_ods_wb_advert_product,
    crud_ods_wb_advert_stat,
    crud_ods_wb_advert_stat_hourly,
    crud_ods_wb_balance,
    crud_ods_wb_cashback,
    crud_ods_wb_chat_event,
    crud_ods_wb_fbs_supply,
    crud_ods_wb_feedback,
    crud_ods_wb_feedback_pin,
    crud_ods_wb_goods_return,
    crud_ods_wb_marketplace_order,
    crud_ods_wb_marketplace_order_status_history,
    crud_ods_wb_new_order,
    crud_ods_wb_order_metadata,
    crud_ods_wb_product_search_text,
    crud_ods_wb_question,
    crud_ods_wb_region_sale,
    crud_ods_wb_reshipment_order,
    crud_ods_wb_return_claim,
    crud_ods_wb_sales_funnel,
    crud_ods_wb_sales_report,
    crud_ods_wb_sales_report_daily,
    crud_ods_wb_sales_report_list,
    crud_ods_wb_search_cluster_stat,
    crud_ods_wb_search_cluster_stat_hourly,
    crud_ods_wb_search_traffic,
    crud_ods_wb_seller_balance,
    crud_ods_wb_supplier_order,
    crud_ods_wb_supplier_sale,
)
from kunpeng.crud.ods.wildberries.adv_enhanced import (
    crud_ods_wb_advert_full_stat,
    crud_ods_wb_advert_v2,
    crud_ods_wb_bid_recommendation,
    crud_ods_wb_norm_query_bid,
    crud_ods_wb_norm_query_list,
    crud_ods_wb_norm_query_minus,
    crud_ods_wb_norm_query_stat,
    crud_ods_wb_promotion_count,
)
from kunpeng.crud.ods.wildberries.advert_budget import CRUDODSWBAdvertBudget
from kunpeng.crud.ods.wildberries.advert_product import CRUDODSWBAdvertProduct
from kunpeng.crud.ods.wildberries.advert_stats_hourly import CRUDODSWBAdvertStatHourly
from kunpeng.crud.ods.wildberries.adverts import CRUDODSWBAdvert, CRUDODSWBAdvertStat
from kunpeng.crud.ods.wildberries.balance import CRUDODSWBBalance, CRUDODSWBCashback
from kunpeng.crud.ods.wildberries.chat_events import CRUDODSWBChatEvent
from kunpeng.crud.ods.wildberries.feedback_pins import CRUDODSWBFeedbackPin
from kunpeng.crud.ods.wildberries.feedbacks import CRUDODSWBFeedback, CRUDODSWBQuestion
from kunpeng.crud.ods.wildberries.finance import CRUDODSWBSalesReport
from kunpeng.crud.ods.wildberries.funnel import (
    CRUDODSWBGoodsReturn,
    CRUDODSWBSalesFunnel,
)
from kunpeng.crud.ods.wildberries.marketplace import (
    CRUDODSWBMarketplaceOrder,
    CRUDODSWBMarketplaceOrderStatusHistory,
)
from kunpeng.crud.ods.wildberries.order_metadata import CRUDODSWBOrderMetadata
from kunpeng.crud.ods.wildberries.product_search_text import CRUDODSWBProductSearchText
from kunpeng.crud.ods.wildberries.region_sale import CRUDODSWBRegionSale
from kunpeng.crud.ods.wildberries.reshipment_orders import CRUDODSWBReshipmentOrder
from kunpeng.crud.ods.wildberries.return_claims import CRUDODSWBReturnClaim

# We need to import the CRUD classes too
from kunpeng.crud.ods.wildberries.sales import (
    CRUDODSWBSupplierOrder,
    CRUDODSWBSupplierSale,
)
from kunpeng.crud.ods.wildberries.sales_report_list import CRUDODSWBSalesReportList
from kunpeng.crud.ods.wildberries.search_cluster_stat import CRUDODSWBSearchClusterStat
from kunpeng.crud.ods.wildberries.search_cluster_stat_hourly import (
    CRUDODSWBSearchClusterStatHourly,
)
from kunpeng.crud.ods.wildberries.search_traffic import CRUDODSWBSearchTraffic
from kunpeng.crud.ods.wildberries.seller_balance import CRUDODSWBSellerBalance
from kunpeng.crud.ods.wildberries.supplies import CRUDODSWBFbsSupply

__all__ = [
    "crud_ods_wb_supplier_sale",
    "crud_ods_wb_supplier_order",
    "CRUDODSWBSupplierSale",
    "CRUDODSWBSupplierOrder",
    "crud_ods_wb_sales_funnel",
    "crud_ods_wb_goods_return",
    "crud_ods_wb_return_claim",
    "crud_ods_wb_chat_event",
    "crud_ods_wb_feedback_pin",
    "CRUDODSWBSalesFunnel",
    "CRUDODSWBGoodsReturn",
    "CRUDODSWBReturnClaim",
    "CRUDODSWBChatEvent",
    "CRUDODSWBFeedbackPin",
    "crud_ods_wb_marketplace_order",
    "crud_ods_wb_marketplace_order_status_history",
    "CRUDODSWBMarketplaceOrder",
    "CRUDODSWBMarketplaceOrderStatusHistory",
    "crud_ods_wb_order_metadata",
    "CRUDODSWBOrderMetadata",
    "crud_ods_wb_fbs_supply",
    "CRUDODSWBFbsSupply",
    "crud_ods_wb_reshipment_order",
    "CRUDODSWBReshipmentOrder",
    "crud_ods_wb_advert",
    "crud_ods_wb_advert_stat",
    "CRUDODSWBAdvert",
    "CRUDODSWBAdvertStat",
    "crud_ods_wb_feedback",
    "crud_ods_wb_question",
    "CRUDODSWBFeedback",
    "CRUDODSWBQuestion",
    "crud_ods_wb_sales_report",
    "crud_ods_wb_sales_report_daily",
    "CRUDODSWBSalesReport",
    "crud_ods_wb_sales_report_list",
    "CRUDODSWBSalesReportList",
    "crud_ods_wb_balance",
    "crud_ods_wb_cashback",
    "CRUDODSWBBalance",
    "CRUDODSWBCashback",
    "crud_ods_wb_advert_product",
    "crud_ods_wb_advert_budget",
    "CRUDODSWBAdvertProduct",
    "CRUDODSWBAdvertBudget",
    "crud_ods_wb_search_cluster_stat",
    "CRUDODSWBSearchClusterStat",
    "crud_ods_wb_advert_stat_hourly",
    "CRUDODSWBAdvertStatHourly",
    "crud_ods_wb_search_cluster_stat_hourly",
    "CRUDODSWBSearchClusterStatHourly",
    "crud_ods_wb_new_order",
    "crud_ods_wb_seller_balance",
    "CRUDODSWBProductSearchText",
    "crud_ods_wb_product_search_text",
    "CRUDODSWBSearchTraffic",
    "crud_ods_wb_search_traffic",
    "CRUDODSWBSellerBalance",
    "crud_ods_wb_region_sale",
    "CRUDODSWBRegionSale",
    # 增强广告数据 (8个新API)
    "crud_ods_wb_norm_query_bid",
    "crud_ods_wb_norm_query_minus",
    "crud_ods_wb_norm_query_list",
    "crud_ods_wb_norm_query_stat",
    "crud_ods_wb_promotion_count",
    "crud_ods_wb_bid_recommendation",
    "crud_ods_wb_advert_full_stat",
    "crud_ods_wb_advert_v2",
]
