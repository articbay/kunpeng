"""Unified Ozon FBS/FBO order-product detail model."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from kunpeng.core.database import Base


class DWDOzonOrderDetail(Base):
    """One row per Ozon shop, fulfilment type, posting and SKU."""

    __tablename__ = "dwd_ozon_order_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    fulfillment_type = Column(
        String(3), primary_key=True, nullable=False, comment="履约方式（FBS/FBO）"
    )
    posting_number = Column(
        String(100), primary_key=True, nullable=False, comment="发货号码"
    )
    sku = Column(BigInteger, primary_key=True, nullable=False, comment="Ozon SKU")

    source_posting_id = Column(BigInteger, nullable=True, comment="ODS订单主表ID")
    source_product_id = Column(BigInteger, nullable=True, comment="ODS订单商品表ID")
    order_type_name = Column(String(30), nullable=False, comment="订单类型")
    order_id = Column(BigInteger, nullable=True, comment="Ozon订单ID")
    order_number = Column(String(100), nullable=True, comment="订单号")

    in_process_month = Column(Date, nullable=True, comment="正在处理中（月）")
    in_process_date = Column(Date, nullable=True, comment="正在处理中（日）")
    in_process_hour = Column(Integer, nullable=True, comment="正在处理中（时）")
    in_process_at = Column(DateTime(timezone=True), nullable=True, comment="正在处理中")
    shipment_date = Column(DateTime(timezone=True), nullable=True, comment="发运日期")
    status_code = Column(String(50), nullable=True, comment="订单状态编码")
    substatus_code = Column(String(50), nullable=True, comment="订单子状态编码")
    status_name_cn = Column(String(100), nullable=True, comment="状态")
    delivery_date = Column(DateTime(timezone=True), nullable=True, comment="配送日期")
    transferred_to_delivery_at = Column(
        DateTime(timezone=True), nullable=True, comment="实际转移配送日期"
    )
    delivery_duration_1_hours = Column(
        Numeric(12, 2), nullable=True, comment="配送用时1（小时）"
    )
    delivery_duration_2_hours = Column(
        Numeric(12, 2), nullable=True, comment="配送用时2（小时）"
    )
    delivery_level_1 = Column(String(50), nullable=True, comment="level配送用时1")
    delivery_level_2 = Column(String(50), nullable=True, comment="level配送用时2")

    shipment_amount = Column(Numeric(18, 4), nullable=True, comment="发货的金额")
    shipment_currency = Column(String(10), nullable=True, comment="货件的货币代码")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    offer_id = Column(String(255), nullable=True, comment="货号")
    seller_price = Column(Numeric(18, 4), nullable=True, comment="您的价格")
    product_currency = Column(String(10), nullable=True, comment="商品的货币代码")
    buyer_paid_amount = Column(Numeric(18, 4), nullable=True, comment="已由买家支付")
    buyer_currency = Column(String(10), nullable=True, comment="买家货币代码")
    quantity = Column(Integer, nullable=True, comment="数量")
    delivery_fee = Column(Numeric(18, 4), nullable=True, comment="运费")
    related_posting_number = Column(String(100), nullable=True, comment="关联货件")
    is_marketplace_buyout = Column(Boolean, nullable=True, comment="商品认购")
    old_price = Column(Numeric(18, 4), nullable=True, comment="商品打折前的价格")
    discount_percent = Column(Numeric(10, 4), nullable=True, comment="折扣百分比")
    discount_amount = Column(Numeric(18, 4), nullable=True, comment="折扣（卢布）")
    promotion_actions = Column(JSON, nullable=True, comment="促销活动")
    product_volume_weight = Column(
        Numeric(12, 4), nullable=True, comment="商品的体积重量（公斤）"
    )

    cluster_from = Column(String(255), nullable=True, comment="发运集群")
    cluster_to = Column(String(255), nullable=True, comment="配送集群")
    promised_delivery_at = Column(
        DateTime(timezone=True), nullable=True, comment="规定配送至买家的时间"
    )
    shipment_assessment = Column(String(255), nullable=True, comment="发运评估")
    ozon_warehouse_name = Column(
        String(255), nullable=True, comment="发运的仓库（Ozon官仓）"
    )
    delivery_region = Column(String(255), nullable=True, comment="配送地区")
    delivery_city = Column(String(255), nullable=True, comment="配送城市")
    delivery_city_cn = Column(String(255), nullable=True, comment="配送城市（中文）")
    delivery_type = Column(String(100), nullable=True, comment="配送方式")
    is_premium = Column(Boolean, nullable=True, comment="买家细分（是否Premium）")
    is_legal = Column(Boolean, nullable=True, comment="法人")
    payment_type = Column(String(255), nullable=True, comment="付款方式")

    buyer_address = Column(Text, nullable=True, comment="买家地址")
    buyer_name = Column(String(255), nullable=True, comment="买家姓名")
    buyer_email = Column(String(255), nullable=True, comment="买家的电子邮箱")
    addressee_name = Column(String(255), nullable=True, comment="收件人姓名")
    buyer_phone = Column(String(100), nullable=True, comment="收件人的电话号码")
    delivery_address = Column(Text, nullable=True, comment="配送地址")
    postal_code = Column(String(50), nullable=True, comment="邮政编码")

    seller_warehouse_name = Column(
        String(255), nullable=True, comment="发运的仓库（第三方仓）"
    )
    shipment_method = Column(String(100), nullable=True, comment="发运方法")
    logistics_company = Column(String(255), nullable=True, comment="物流公司")
    delivery_method_name = Column(String(255), nullable=True, comment="方式名称")
    shipment_date_without_delay = Column(
        DateTime(timezone=True), nullable=True, comment="不逾期的发运日期"
    )
    cancellation_at = Column(DateTime(timezone=True), nullable=True, comment="取消日期")
    declared_total_weight = Column(
        Numeric(12, 4), nullable=True, comment="申报的货件总重量"
    )
    actual_total_weight = Column(
        Numeric(12, 4), nullable=True, comment="货件的实际总重量"
    )
    shipment_volume_weight = Column(
        Numeric(12, 4), nullable=True, comment="货件的总体积重量"
    )
    product_color = Column(String(255), nullable=True, comment="商品颜色")
    product_size = Column(String(255), nullable=True, comment="商品尺寸")

    create_time = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
    update_time = Column(
        DateTime(timezone=True), nullable=True, onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (
        Index("idx_dwd_ozon_order_order_number", "shop_id", "order_number"),
        Index("idx_dwd_ozon_order_in_process", "shop_id", "in_process_at"),
        Index("idx_dwd_ozon_order_status", "shop_id", "status_code"),
        Index("idx_dwd_ozon_order_offer", "shop_id", "offer_id"),
        {
            "comment": "Ozon FBS/FBO统一订单商品明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
