"""Ozon order-product lifecycle detail model."""

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text, text
from sqlalchemy.sql import func

from kunpeng.core.database import Base


class DWMOzonOrderLifecycleDetail(Base):
    """One row per Ozon shop, fulfilment type, posting and SKU."""

    __tablename__ = "dwm_ozon_order_lifecycle_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    fulfillment_type = Column(
        String(3), primary_key=True, nullable=False, comment="履约方式（FBS/FBO）"
    )
    posting_number = Column(
        String(100), primary_key=True, nullable=False, comment="发货号码"
    )
    sku = Column(BigInteger, primary_key=True, nullable=False, comment="Ozon SKU")

    order_id = Column(BigInteger, nullable=True, comment="Ozon订单ID")
    order_number = Column(String(100), nullable=True, comment="订单号")
    offer_id = Column(String(255), nullable=True, comment="货号")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    quantity = Column(Integer, nullable=True, comment="下单数量")

    status_code = Column(String(50), nullable=True, comment="订单当前状态编码")
    substatus_code = Column(String(50), nullable=True, comment="订单当前子状态编码")
    status_name_cn = Column(String(100), nullable=True, comment="订单当前状态中文")

    in_process_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="进入处理时间，业务上近似作为下单时间",
    )
    shipment_date = Column(
        DateTime(timezone=True), nullable=True, comment="实际发货日期"
    )
    transferred_to_delivery_at = Column(
        DateTime(timezone=True), nullable=True, comment="实际移交配送日期"
    )
    delivery_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="送往自提点/进入实际配送日期",
    )
    promised_delivery_at = Column(
        DateTime(timezone=True), nullable=True, comment="承诺送达时间"
    )
    cancellation_at = Column(DateTime(timezone=True), nullable=True, comment="取消日期")

    return_cnt = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="退货记录数",
    )
    return_qty = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="累计退货数量",
    )
    first_return_date = Column(
        DateTime(timezone=True), nullable=True, comment="首次退货日期"
    )
    latest_return_id = Column(BigInteger, nullable=True, comment="最新退货记录ID")
    latest_return_status_sys_name = Column(
        String(255), nullable=True, comment="最新退货状态编码"
    )
    latest_return_status_display_name_cn = Column(
        String(255), nullable=True, comment="最新退货状态中文"
    )
    latest_return_status_change_at = Column(
        DateTime(timezone=True), nullable=True, comment="最新退货状态变更时间"
    )
    latest_return_reason_name_cn = Column(
        Text, nullable=True, comment="最新退货原因中文"
    )
    last_ready_to_pickup_at = Column(
        DateTime(timezone=True), nullable=True, comment="最近一次到达取货点时间"
    )
    last_picked_up_at = Column(
        DateTime(timezone=True), nullable=True, comment="最近一次向卖家退货时间"
    )

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
        Index("idx_dwm_ozon_lifecycle_order", "shop_id", "order_number"),
        Index("idx_dwm_ozon_lifecycle_in_process", "shop_id", "in_process_at"),
        Index("idx_dwm_ozon_lifecycle_sku", "shop_id", "sku"),
        Index("idx_dwm_ozon_lifecycle_status", "shop_id", "status_code"),
        {
            "comment": "DWM-Ozon订单商品生命周期明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
