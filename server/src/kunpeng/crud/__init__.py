# CRUD层模块
from kunpeng.crud.base import CRUDBase
from kunpeng.crud.user import user_crud
from kunpeng.crud.shop import shop_crud

# ODS 层 CRUD
from kunpeng.crud.ods import (
    crud_ods_wb_supplier_sale,
    crud_ods_wb_supplier_order,
    crud_ods_wb_sales_funnel,
    crud_ods_wb_goods_return,
    crud_ods_wb_marketplace_order,
    crud_ods_wb_advert,
    crud_ods_wb_advert_stat,
    crud_ods_wb_feedback,
    crud_ods_wb_question,
    crud_ods_wb_sales_report,
    CRUDODSWBSupplierSale,
    CRUDODSWBSupplierOrder,
    CRUDODSWBSalesFunnel,
    CRUDODSWBGoodsReturn,
    CRUDODSWBMarketplaceOrder,
    CRUDODSWBAdvert,
    CRUDODSWBAdvertStat,
    CRUDODSWBFeedback,
    CRUDODSWBQuestion,
    CRUDODSWBSalesReport,
)

__all__ = [
    "CRUDBase",
    "user_crud",
    "shop_crud",
    # ODS 层 CRUD
    "crud_ods_wb_supplier_sale",
    "crud_ods_wb_supplier_order",
    "crud_ods_wb_sales_funnel",
    "crud_ods_wb_goods_return",
    "crud_ods_wb_marketplace_order",
    "crud_ods_wb_advert",
    "crud_ods_wb_advert_stat",
    "crud_ods_wb_feedback",
    "crud_ods_wb_question",
    "crud_ods_wb_sales_report",
    "CRUDODSWBSupplierSale",
    "CRUDODSWBSupplierOrder",
    "CRUDODSWBSalesFunnel",
    "CRUDODSWBGoodsReturn",
    "CRUDODSWBMarketplaceOrder",
    "CRUDODSWBAdvert",
    "CRUDODSWBAdvertStat",
    "CRUDODSWBFeedback",
    "CRUDODSWBQuestion",
    "CRUDODSWBSalesReport",
]
