"""Wildberries ODS CRUD。"""

from .adv_enhanced import (
    crud_ods_wb_advert_full_stat,
    crud_ods_wb_advert_v2,
    crud_ods_wb_bid_recommendation,
    crud_ods_wb_norm_query_bid,
    crud_ods_wb_norm_query_list,
    crud_ods_wb_norm_query_minus,
    crud_ods_wb_norm_query_stat,
    crud_ods_wb_promotion_count,
)
from .advert_budget import crud_ods_wb_advert_budget
from .advert_product import crud_ods_wb_advert_product
from .advert_stats_hourly import (
    CRUDODSWBAdvertStatHourly,
    crud_ods_wb_advert_stat_hourly,
)
from .adverts import crud_ods_wb_advert, crud_ods_wb_advert_stat
from .balance import crud_ods_wb_balance, crud_ods_wb_cashback
from .chat_events import crud_ods_wb_chat_event
from .feedback_pins import crud_ods_wb_feedback_pin
from .feedbacks import crud_ods_wb_feedback, crud_ods_wb_question
from .finance import crud_ods_wb_sales_report
from .finance_daily import crud_ods_wb_sales_report_daily
from .funnel import crud_ods_wb_goods_return, crud_ods_wb_sales_funnel
from .marketplace import (
    crud_ods_wb_marketplace_order,
    crud_ods_wb_marketplace_order_status_history,
)
from .new_orders import crud_ods_wb_new_order
from .order_metadata import crud_ods_wb_order_metadata
from .product_search_text import (
    CRUDODSWBProductSearchText,
    crud_ods_wb_product_search_text,
)
from .region_sale import CRUDODSWBRegionSale, crud_ods_wb_region_sale
from .reshipment_orders import crud_ods_wb_reshipment_order
from .return_claims import crud_ods_wb_return_claim
from .sales import crud_ods_wb_supplier_order, crud_ods_wb_supplier_sale
from .sales_report_list import CRUDODSWBSalesReportList, crud_ods_wb_sales_report_list
from .search_cluster_stat import crud_ods_wb_search_cluster_stat
from .search_cluster_stat_hourly import (
    CRUDODSWBSearchClusterStatHourly,
    crud_ods_wb_search_cluster_stat_hourly,
)
from .search_traffic import CRUDODSWBSearchTraffic, crud_ods_wb_search_traffic
from .seller_balance import CRUDODSWBSellerBalance, crud_ods_wb_seller_balance
from .supplies import crud_ods_wb_fbs_supply

__all__ = [
    "crud_ods_wb_supplier_sale",
    "crud_ods_wb_supplier_order",
    "crud_ods_wb_sales_funnel",
    "crud_ods_wb_goods_return",
    "crud_ods_wb_return_claim",
    "crud_ods_wb_chat_event",
    "crud_ods_wb_feedback_pin",
    "crud_ods_wb_advert",
    "crud_ods_wb_advert_stat",
    "crud_ods_wb_feedback",
    "crud_ods_wb_question",
    "crud_ods_wb_sales_report",
    "crud_ods_wb_sales_report_daily",
    "crud_ods_wb_sales_report_list",
    "CRUDODSWBSalesReportList",
    "crud_ods_wb_marketplace_order",
    "crud_ods_wb_marketplace_order_status_history",
    "crud_ods_wb_balance",
    "crud_ods_wb_cashback",
    "crud_ods_wb_advert_product",
    "crud_ods_wb_advert_budget",
    "crud_ods_wb_search_cluster_stat",
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
    "crud_ods_wb_order_metadata",
    "crud_ods_wb_fbs_supply",
    "crud_ods_wb_reshipment_order",
    "crud_ods_wb_norm_query_bid",
    "crud_ods_wb_norm_query_minus",
    "crud_ods_wb_norm_query_list",
    "crud_ods_wb_norm_query_stat",
    "crud_ods_wb_promotion_count",
    "crud_ods_wb_bid_recommendation",
    "crud_ods_wb_advert_full_stat",
    "crud_ods_wb_advert_v2",
]
