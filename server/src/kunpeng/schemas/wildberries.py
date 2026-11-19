"""
Wildberries Pydantic Schemas
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

# ==================== 基础响应模型 ====================


class WBBaseResponse(BaseModel):
    """基础响应模型"""

    model_config = ConfigDict(from_attributes=True)


# ==================== 销售数据相关 ====================


class WBSaleBase(WBBaseResponse):
    """销售数据基础"""

    srid: Optional[str] = None
    g_number: Optional[str] = None
    date: Optional[datetime] = None
    last_change_date: Optional[datetime] = None
    supply_id: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    tech_size: Optional[str] = None
    barcode: Optional[str] = None
    subject: Optional[str] = None
    brand: Optional[str] = None
    total_price: Optional[Decimal] = None
    finished_price: Optional[Decimal] = None
    price_with_disc: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    spp: Optional[Decimal] = None
    is_cancel: Optional[bool] = None
    cancel_date: Optional[datetime] = None
    warehouse_name: Optional[str] = None
    country_name: Optional[str] = None
    region_name: Optional[str] = None


class WBSaleCreate(WBSaleBase):
    """创建销售数据"""

    shop_id: int


class WBSaleUpdate(WBSaleBase):
    """更新销售数据"""

    pass


class WBSaleResponse(WBSaleBase):
    """销售数据响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class WBOrderBase(WBBaseResponse):
    """订单数据基础"""

    srid: Optional[str] = None
    g_number: Optional[str] = None
    odid: Optional[str] = None
    date: Optional[datetime] = None
    last_change_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    supply_id: Optional[str] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    tech_size: Optional[str] = None
    barcode: Optional[str] = None
    subject: Optional[str] = None
    brand: Optional[str] = None
    total_price: Optional[Decimal] = None
    finished_price: Optional[Decimal] = None
    price_with_disc: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    spp: Optional[Decimal] = None
    is_cancel: Optional[bool] = None
    cancel_date: Optional[datetime] = None
    order_type: Optional[str] = None
    warehouse_name: Optional[str] = None
    country_name: Optional[str] = None
    region_name: Optional[str] = None
    sticker: Optional[str] = None


class WBOrderCreate(WBOrderBase):
    """创建订单数据"""

    shop_id: int


class WBOrderResponse(WBOrderBase):
    """订单数据响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 销售漏斗相关 ====================


class WBSalesFunnelBase(WBBaseResponse):
    """销售漏斗基础"""

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    nm_id: Optional[int] = None
    vendor_code: Optional[str] = None
    title: Optional[str] = None
    subject_name: Optional[str] = None
    brand_name: Optional[str] = None
    is_deleted: Optional[bool] = None
    open_count: Optional[int] = None
    add_to_cart_count: Optional[int] = None
    add_to_favorites_count: Optional[int] = None
    orders_count: Optional[int] = None
    buyouts_count: Optional[int] = None
    cancel_count: Optional[int] = None
    cart_to_order_conversion: Optional[Decimal] = None
    order_to_buyout_conversion: Optional[Decimal] = None
    view_to_buyout_conversion: Optional[Decimal] = None
    ordered_amount: Optional[Decimal] = None
    buyouts_amount: Optional[Decimal] = None
    canceled_amount: Optional[Decimal] = None


class WBSalesFunnelCreate(WBSalesFunnelBase):
    """创建销售漏斗"""

    shop_id: int


class WBSalesFunnelResponse(WBSalesFunnelBase):
    """销售漏斗响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class WBSalesFunnelListItem(WBBaseResponse):
    vendor_code: Optional[str] = None
    nm_id: Optional[int] = None
    subject_name: Optional[str] = None
    brand_name: Optional[str] = None
    tags: Optional[Any] = None
    product_rating: Optional[int] = None
    feedback_rating: Optional[Decimal] = None
    open_count: Optional[int] = None
    cart_count: Optional[int] = None
    add_to_wishlist: Optional[int] = None


class WBSalesFunnelDetailItem(WBBaseResponse):
    """DWD 销售漏斗商品明细查询响应。"""

    id: int
    shop_id: int
    date_from: date
    date_to: date
    vendor_code: Optional[str] = None
    nm_id: int
    title: Optional[str] = None
    subject_name: Optional[str] = None
    brand_name: Optional[str] = None
    tags: Optional[Any] = None
    product_rating: Optional[int] = None
    feedback_rating: Optional[Decimal] = None
    open_count: Optional[int] = None
    cart_count: Optional[int] = None
    add_to_wishlist: Optional[int] = None
    order_count: Optional[int] = None
    buyout_count: Optional[int] = None
    cancel_count: Optional[int] = None
    add_to_cart_percent: Optional[Decimal] = None
    cart_to_order_percent: Optional[Decimal] = None
    buyout_percent: Optional[Decimal] = None
    order_sum: Optional[Decimal] = None
    buyout_sum: Optional[Decimal] = None
    cancel_sum: Optional[Decimal] = None
    create_time: datetime
    update_time: Optional[datetime] = None


class WBSalesReportSummaryItem(WBBaseResponse):
    """DWD 财务报告周汇总查询响应。"""

    id: int
    shop_id: int
    report_id: int
    seller_finance_name: Optional[str] = None
    date_from: date
    date_to: date
    create_date: Optional[date] = None
    report_type: Optional[int] = None
    retail_amount_sum: Optional[Decimal] = None
    cashback_discount_sum: Optional[Decimal] = None
    for_pay_sum: Optional[Decimal] = None
    avg_sale_percent: Optional[Decimal] = None
    delivery_service_sum: Optional[Decimal] = None
    paid_storage_sum: Optional[Decimal] = None
    paid_acceptance_sum: Optional[Decimal] = None
    deduction_sum: Optional[Decimal] = None
    penalty_sum: Optional[Decimal] = None
    additional_payment_sum: Optional[Decimal] = None
    cashback_commission_change_sum: Optional[Decimal] = None
    cashback_amount_sum: Optional[Decimal] = None
    payment_schedule: Optional[Decimal] = None
    bank_payment_sum: Optional[Decimal] = None
    currency: Optional[str] = None
    create_time: datetime
    update_time: Optional[datetime] = None


# ==================== 广告相关 ====================


class WBFinancialReportDetailItem(WBBaseResponse):
    """DWD 财务报告周明细查询响应。"""

    id: int
    shop_id: int
    date_from: date
    rrd_id: int
    gi_id: Optional[int] = None
    subject_name: Optional[str] = None
    nm_id: Optional[int] = None
    brand_name: Optional[str] = None
    vendor_code: Optional[str] = None
    title: Optional[str] = None
    tech_size: Optional[str] = None
    sku: Optional[str] = None
    doc_type_name: Optional[str] = None
    seller_oper_name: Optional[str] = None
    order_dt: Optional[datetime] = None
    sale_dt: Optional[datetime] = None
    quantity: Optional[int] = None
    retail_price: Optional[Decimal] = None
    retail_amount: Optional[Decimal] = None
    sale_percent: Optional[Decimal] = None
    seller_promo: Optional[Decimal] = None
    product_discount_for_report: Optional[Decimal] = None
    retail_price_with_disc: Optional[Decimal] = None
    sup_rating_up: Optional[int] = None
    is_kgvp_v2: Optional[int] = None
    spp: Optional[Decimal] = None
    commission_percent: Optional[Decimal] = None
    kvw_base: Optional[Decimal] = None
    kvw: Optional[Decimal] = None
    ppvz_sales_commission: Optional[Decimal] = None
    ppvz_reward: Optional[Decimal] = None
    acquiring_fee: Optional[Decimal] = None
    acquiring_percent: Optional[Decimal] = None
    payment_processing: Optional[str] = None
    vw: Optional[Decimal] = None
    vw_nds: Optional[Decimal] = None
    for_pay: Optional[Decimal] = None
    delivery_amount: Optional[int] = None
    return_amount: Optional[int] = None
    delivery_service: Optional[Decimal] = None
    dlv_prc: Optional[int] = None
    fix_tariff_date_from: Optional[str] = None
    fix_tariff_date_to: Optional[str] = None
    srv_dbs: Optional[bool] = None
    penalty: Optional[Decimal] = None
    additional_payment: Optional[Decimal] = None
    bonus_type_name: Optional[str] = None
    shk_id: Optional[int] = None
    acquiring_bank: Optional[str] = None
    ppvz_office_id: Optional[int] = None
    ppvz_office_name: Optional[str] = None
    ppvz_supplier_inn: Optional[str] = None
    ppvz_supplier_name: Optional[str] = None
    office_name: Optional[str] = None
    country: Optional[str] = None
    gi_box_type_name: Optional[str] = None
    declaration_number: Optional[str] = None
    order_id: Optional[int] = None
    kiz: Optional[str] = None
    sticker_id: Optional[str] = None
    srid: Optional[str] = None
    rebill_logistic_cost: Optional[Decimal] = None
    rebill_logistic_org: Optional[str] = None
    paid_storage: Optional[Decimal] = None
    deduction: Optional[Decimal] = None
    paid_acceptance: Optional[Decimal] = None
    is_b2b: Optional[bool] = None
    trbx_id: Optional[str] = None
    installment_cofinancing_amount: Optional[Decimal] = None
    wibes_discount_percent: Optional[Decimal] = None
    cashback_discount: Optional[Decimal] = None
    cashback_commission_change: Optional[Decimal] = None
    cashback_amount: Optional[Decimal] = None
    order_uid: Optional[str] = None
    payment_schedule: Optional[str] = None
    delivery_method: Optional[str] = None


class WBAdvertBase(WBBaseResponse):
    """广告活动基础"""

    advert_id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[int] = None
    bid_type: Optional[str] = None


class WBAdvertCreate(WBAdvertBase):
    """创建广告活动"""

    shop_id: int


class WBAdvertResponse(WBAdvertBase):
    """广告活动响应"""

    id: int
    shop_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WBAdvertStatBase(WBBaseResponse):
    """广告统计基础"""

    advert_id: Optional[int] = None
    stat_date: Optional[datetime] = None
    views: Optional[int] = None
    clicks: Optional[int] = None
    at_cart: Optional[int] = None
    orders: Optional[int] = None
    sum: Optional[Decimal] = None
    ctr: Optional[Decimal] = None
    cpc: Optional[Decimal] = None
    cr: Optional[Decimal] = None


class WBAdvertStatCreate(WBAdvertStatBase):
    """创建广告统计"""

    shop_id: int


class WBAdvertStatResponse(WBAdvertStatBase):
    """广告统计响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 退货相关 ====================


class WBReturnBase(WBBaseResponse):
    """退货数据基础"""

    srid: Optional[str] = None
    rrd_id: Optional[str] = None
    date: Optional[datetime] = None
    last_change_date: Optional[datetime] = None
    order_dt: Optional[datetime] = None
    sale_dt: Optional[datetime] = None
    nm_id: Optional[int] = None
    supplier_article: Optional[str] = None
    barcode: Optional[str] = None
    subject_name: Optional[str] = None
    brand_name: Optional[str] = None
    ts_name: Optional[str] = None
    status: Optional[str] = None
    is_cancel: Optional[bool] = None
    quantity: Optional[int] = None
    retail_amount: Optional[Decimal] = None
    ppvz_for_pay: Optional[Decimal] = None


class WBReturnCreate(WBReturnBase):
    """创建退货数据"""

    shop_id: int


class WBReturnResponse(WBReturnBase):
    """退货数据响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 评价相关 ====================


class WBFeedbackBase(WBBaseResponse):
    """评价数据基础"""

    feedback_id: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    nm_id: Optional[int] = None
    product_details: Optional[Dict[str, Any]] = None
    supplier_article: Optional[str] = None
    brand_name: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    product_valuation: Optional[int] = None
    text: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    user_name: Optional[str] = None
    subject_name: Optional[str] = None
    is_answered: Optional[bool] = None
    answer: Optional[Dict[str, Any]] = None
    supplier_feedback_valuation: Optional[int] = None
    parent_feedback_id: Optional[str] = None
    child_feedback_id: Optional[str] = None


class WBFeedbackCreate(WBFeedbackBase):
    """创建评价数据"""

    shop_id: int


class WBFeedbackResponse(WBFeedbackBase):
    """评价数据响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 提问相关 ====================


class WBQuestionBase(WBBaseResponse):
    """提问数据基础"""

    question_id: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    nm_id: Optional[int] = None
    product_details: Optional[Dict[str, Any]] = None
    supplier_article: Optional[str] = None
    brand_name: Optional[str] = None
    text: Optional[str] = None
    is_answered: Optional[bool] = None
    answer: Optional[Dict[str, Any]] = None


class WBQuestionCreate(WBQuestionBase):
    """创建提问数据"""

    shop_id: int


class WBQuestionResponse(WBQuestionBase):
    """提问数据响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 财务相关 ====================


class WBFinanceReportBase(WBBaseResponse):
    """财务报告基础"""

    realizationreport_id: Optional[int] = None
    report_type: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    create_dt: Optional[datetime] = None
    currency_name: Optional[str] = None
    retail_amount_sum: Optional[Decimal] = None
    cashback_discount_sum: Optional[Decimal] = None
    ppvz_for_pay_sum: Optional[Decimal] = None
    delivery_rub_sum: Optional[Decimal] = None
    storage_fee_sum: Optional[Decimal] = None
    acceptance_sum: Optional[Decimal] = None
    penalty_sum: Optional[Decimal] = None
    deduction_sum: Optional[Decimal] = None
    additional_payment_sum: Optional[Decimal] = None
    cashback_amount_sum: Optional[Decimal] = None
    cashback_commission_change_sum: Optional[Decimal] = None
    payment_schedule_sum: Optional[Decimal] = None
    total_payable: Optional[Decimal] = None


class WBFinanceReportCreate(WBFinanceReportBase):
    """创建财务报告"""

    shop_id: int


class WBFinanceReportResponse(WBFinanceReportBase):
    """财务报告响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class WBFinanceReportItemBase(WBBaseResponse):
    """财务报告明细基础"""

    report_id: Optional[int] = None
    rrd_id: Optional[str] = None
    gi_id: Optional[str] = None
    srid: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    create_dt: Optional[datetime] = None
    nm_id: Optional[int] = None
    sa_name: Optional[str] = None
    sku: Optional[str] = None
    subject_name: Optional[str] = None
    brand_name: Optional[str] = None
    ts_name: Optional[str] = None
    doc_type_name: Optional[str] = None
    supplier_oper_name: Optional[str] = None
    bonus_type_name: Optional[str] = None
    order_dt: Optional[datetime] = None
    sale_dt: Optional[datetime] = None
    quantity: Optional[int] = None
    delivery_amount: Optional[int] = None
    return_amount: Optional[int] = None
    retail_price: Optional[Decimal] = None
    retail_amount: Optional[Decimal] = None
    product_discount_for_report: Optional[Decimal] = None
    supplier_promo: Optional[Decimal] = None
    sale_percent: Optional[Decimal] = None
    retail_price_withdisc_rub: Optional[Decimal] = None
    commission_percent: Optional[Decimal] = None
    ppvz_kvw_prc_base: Optional[Decimal] = None
    ppvz_kvw_prc: Optional[Decimal] = None
    ppvz_sales_commission: Optional[Decimal] = None
    ppvz_vw: Optional[Decimal] = None
    ppvz_vw_nds: Optional[Decimal] = None
    ppvz_for_pay: Optional[Decimal] = None
    delivery_rub: Optional[Decimal] = None
    storage_fee: Optional[Decimal] = None
    acceptance: Optional[Decimal] = None
    dlv_prc: Optional[Decimal] = None
    penalty: Optional[Decimal] = None
    deduction: Optional[Decimal] = None
    additional_payment: Optional[Decimal] = None
    cashback_discount: Optional[Decimal] = None
    cashback_amount: Optional[Decimal] = None
    cashback_commission_change: Optional[Decimal] = None
    acquiring_fee: Optional[Decimal] = None
    acquiring_percent: Optional[Decimal] = None
    acquiring_bank: Optional[str] = None
    office_name: Optional[str] = None
    ppvz_office_id: Optional[int] = None
    ppvz_office_name: Optional[str] = None
    ppvz_inn: Optional[str] = None
    ppvz_supplier_name: Optional[str] = None
    site_country: Optional[str] = None
    sticker_id: Optional[str] = None
    shk_id: Optional[str] = None
    declaration_number: Optional[str] = None
    assembly_id: Optional[str] = None
    trbx_id: Optional[str] = None
    gi_box_type_name: Optional[str] = None
    rebill_logistic_org: Optional[str] = None
    payment_schedule: Optional[str] = None
    order_uid: Optional[str] = None
    delivery_method: Optional[str] = None
    srv_dbs: Optional[str] = None
    is_legal_entity: Optional[bool] = None
    wibes_wb_discount_percent: Optional[Decimal] = None
    sup_rating_prc_up: Optional[Decimal] = None
    ppvz_spp_prc: Optional[Decimal] = None
    fix_tariff_date_from: Optional[datetime] = None
    fix_tariff_date_to: Optional[datetime] = None
    payment_processing: Optional[str] = None


class WBFinanceReportItemCreate(WBFinanceReportItemBase):
    """创建财务报告明细"""

    shop_id: int


class WBFinanceReportItemResponse(WBFinanceReportItemBase):
    """财务报告明细响应"""

    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 同步相关 ====================


class WBSyncRequest(BaseModel):
    """同步请求"""

    shop_id: int
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None  # YYYY-MM-DD
    sync_types: Optional[List[str]] = (
        None  # 要同步的数据类型: sales, orders, funnel, adverts, returns, feedbacks, questions, finance
    )


class WBSyncResponse(BaseModel):
    """同步响应"""

    status: str
    message: str
    synced_count: Optional[Dict[str, int]] = None
    results: Optional[Dict[str, Dict[str, Any]]] = None


# ==================== DWD广告周度报表相关 ====================

class WBAdvertsReportDetailBase(WBBaseResponse):
    """广告周度报表基础"""
    shop_id: Optional[int] = None
    week: Optional[str] = None
    advert_id: Optional[int] = None
    advert_name: Optional[str] = None
    advert_status: Optional[int] = None
    advert_status_label: Optional[str] = None
    paid_views: Optional[int] = None
    paid_clicks: Optional[int] = None
    atbs: Optional[int] = None
    orders: Optional[int] = None
    ctr: Optional[float] = None
    cpc: Optional[float] = None
    cr: Optional[float] = None
    sum_cost: Optional[float] = None
    sum_price: Optional[float] = None


class WBAdvertsReportDetailResponse(WBAdvertsReportDetailBase):
    """广告周度报表响应"""
    id: int
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
