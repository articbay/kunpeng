"""
Ozon ODS 层 - 订单相关表
"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Boolean, DateTime, Date,
    Numeric, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DECIMAL
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonFBSPosting(BaseModel):
    """
    Ozon ODS 层 - FBS订单主表

    描述: 存储Ozon FBS（卖家自发货）订单的主数据，包含订单基本信息、状态、配送方式、时间节点等完整订单信息。
    """

    __tablename__ = "ods_ozon_fbs_postings"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_postings_shop_posting"
        ),
        Index("idx_ods_ozon_postings_shop_id", "shop_id"),
        Index("idx_ods_ozon_postings_in_process_at", "in_process_at"),
        {
            "comment": "Ozon FBS订单主表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    order_number = Column(VARCHAR(100), nullable=True, comment="订单编号")
    status = Column(VARCHAR(50), nullable=True, comment="订单状态")
    substatus = Column(VARCHAR(50), nullable=True, comment="订单子状态")
    delivery_schema = Column(VARCHAR(20), nullable=True, comment="发货模式 (FBO/FBS)")
    tpl_integration_type = Column(VARCHAR(50), nullable=True, comment="集成类型")
    in_process_at = Column(DateTime(timezone=True), nullable=True, comment="处理开始时间")
    shipment_date = Column(DateTime(timezone=True), nullable=True, comment="发货日期")
    shipment_date_without_delay = Column(DateTime(timezone=True), nullable=True, comment="无延迟发货日期")
    delivering_date = Column(DateTime(timezone=True), nullable=True, comment="配送日期")
    tracking_number = Column(VARCHAR(100), nullable=True, comment="物流单号")
    pickup_code_verified_at = Column(DateTime(timezone=True), nullable=True, comment="取件码验证时间")
    destination_place_id = Column(BigInteger, nullable=True, comment="目的地ID")
    destination_place_name = Column(VARCHAR(255), nullable=True, comment="目的地名称")
    is_express = Column(Boolean, nullable=True, comment="是否快递")
    is_multibox = Column(Boolean, nullable=True, comment="是否多箱")
    multi_box_qty = Column(Integer, nullable=True, comment="多箱数量")
    is_presortable = Column(Boolean, nullable=True, comment="是否预分类")
    is_click_and_collect = Column(Boolean, nullable=True, comment="是否点击取件")
    prr_option = Column(VARCHAR(100), nullable=True, comment="PRR选项")
    parent_posting_number = Column(VARCHAR(100), nullable=True, comment="父订单号")
    quantum_id = Column(BigInteger, nullable=True, comment="Quantum ID")
    volume_weight = Column(DECIMAL(10, 4), nullable=True, comment="体积重量")
    require_blr_traceable_attrs = Column(Boolean, nullable=True, comment="是否需要BLR可追溯属性")
    container_sort_type = Column(VARCHAR(50), nullable=True, comment="容器分类类型")
    customer = Column(JSON, nullable=True, comment="客户信息")
    addressee = Column(JSON, nullable=True, comment="收件人信息")
    barcodes = Column(JSON, nullable=True, comment="条码信息")
    analytics_data = Column(JSON, nullable=True, comment="分析数据")
    financial_data = Column(JSON, nullable=True, comment="财务数据")
    legal_info = Column(JSON, nullable=True, comment="法律信息")
    requirements = Column(JSON, nullable=True, comment="要求信息")
    tariffication = Column(JSON, nullable=True, comment="计费信息")
    container = Column(JSON, nullable=True, comment="容器信息")
    available_actions = Column(JSON, nullable=True, comment="可用操作列表")
    tariffication_steps = Column(JSON, nullable=True, comment="计费步骤")
    cursor = Column(VARCHAR(255), nullable=True, comment="分页游标")
    has_next = Column(Boolean, nullable=True, comment="是否有下一页")


class ODSOzonFBSPostingProduct(BaseModel):
    """
    Ozon ODS 层 - FBS订单商品表

    描述: 存储Ozon FBS订单的商品明细数据，包含每个订单的商品SKU、名称、数量、价格、重量等详细商品信息。
    """

    __tablename__ = "ods_ozon_fbs_posting_products"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number", "sku",
            name="uq_ods_ozon_posting_products_shop_posting_sku"
        ),
        Index("idx_ods_ozon_posting_products_posting_id", "posting_id"),
        {
            "comment": "Ozon FBS订单商品表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_id = Column(BigInteger, nullable=True, comment="关联订单ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    sku = Column(BigInteger, nullable=True, comment="商品SKU")
    offer_id = Column(VARCHAR(255), nullable=True, comment="商家SKU")
    name = Column(TEXT, nullable=True, comment="商品名称")
    quantity = Column(Integer, nullable=True, comment="数量")
    price_amount = Column(DECIMAL(18, 4), nullable=True, comment="价格金额")
    price_currency = Column(VARCHAR(10), nullable=True, comment="价格币种")
    weight = Column(DECIMAL(10, 4), nullable=True, comment="重量")
    product_color = Column(VARCHAR(255), nullable=True, comment="商品颜色")
    is_blr_traceable = Column(Boolean, nullable=True, comment="是否可追溯")
    is_marketplace_buyout = Column(Boolean, nullable=True, comment="是否平台买断")
    mandatory_mark = Column(TEXT, nullable=True, comment="强制标识")
    imei = Column(JSON, nullable=True, comment="IMEI列表")


class ODSOzonFBSPostingDelivery(BaseModel):
    """
    Ozon ODS 层 - FBS订单配送信息表

    描述: 存储Ozon FBS订单的配送方式信息，包含配送方式ID、名称、仓库信息、TPL供应商等配送相关数据。
    """

    __tablename__ = "ods_ozon_fbs_posting_delivery"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_posting_delivery_shop_posting"
        ),
        Index("idx_ods_ozon_posting_delivery_posting_id", "posting_id"),
        {
            "comment": "Ozon FBS订单配送信息表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_id = Column(BigInteger, nullable=True, comment="关联订单ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    delivery_id = Column(BigInteger, nullable=True, comment="配送方式ID")
    delivery_name = Column(VARCHAR(255), nullable=True, comment="配送方式名称")
    warehouse_id = Column(BigInteger, nullable=True, comment="仓库ID")
    warehouse_name = Column(VARCHAR(255), nullable=True, comment="仓库名称")
    tpl_provider_id = Column(BigInteger, nullable=True, comment="TPL供应商ID")
    tpl_provider = Column(VARCHAR(255), nullable=True, comment="TPL供应商名称")


class ODSOzonFBSPostingCancellation(BaseModel):
    """
    Ozon ODS 层 - FBS订单取消信息表

    描述: 存储Ozon FBS订单的取消信息，包含取消原因、取消类型、取消发起方、是否影响评分等取消相关数据。
    """

    __tablename__ = "ods_ozon_fbs_posting_cancellation"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_posting_cancellation_shop_posting"
        ),
        Index("idx_ods_ozon_posting_cancellation_posting_id", "posting_id"),
        {
            "comment": "Ozon FBS订单取消信息表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_id = Column(BigInteger, nullable=True, comment="关联订单ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    cancel_reason_id = Column(BigInteger, nullable=True, comment="取消原因ID")
    cancel_reason = Column(TEXT, nullable=True, comment="取消原因")
    cancellation_type = Column(VARCHAR(50), nullable=True, comment="取消类型")
    cancelled_after_ship = Column(Boolean, nullable=True, comment="发货后取消")
    affect_cancellation_rating = Column(Boolean, nullable=True, comment="影响取消评分")
    cancellation_initiator = Column(VARCHAR(100), nullable=True, comment="取消发起方")


class ODSOzonFBSPostingOptional(BaseModel):
    """
    Ozon ODS 层 - FBS订单可选信息表

    描述: 存储Ozon FBS订单的可选扩展信息，包含可能需要强制标识的商品列表等可选字段数据。
    """

    __tablename__ = "ods_ozon_fbs_posting_optional"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_posting_optional_shop_posting"
        ),
        Index("idx_ods_ozon_posting_optional_posting_id", "posting_id"),
        {
            "comment": "Ozon FBS订单可选信息表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_id = Column(BigInteger, nullable=True, comment="关联订单ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    products_with_possible_mandatory_mark = Column(JSON, nullable=True, comment="可能需要强制标识的商品列表")


class ODSOzonFBSPostingExternal(BaseModel):
    """
    Ozon ODS 层 - FBS外部订单信息表

    描述: 存储Ozon FBS外部订单信息，标识订单是否来自外部平台以及平台名称等信息。
    """

    __tablename__ = "ods_ozon_fbs_posting_external"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_posting_external_shop_posting"
        ),
        Index("idx_ods_ozon_posting_external_posting_id", "posting_id"),
        {
            "comment": "Ozon FBS外部订单信息表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_id = Column(BigInteger, nullable=True, comment="关联订单ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    is_external = Column(Boolean, nullable=True, comment="是否外部订单")
    platform_name = Column(VARCHAR(255), nullable=True, comment="平台名称")
