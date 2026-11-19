"""Wildberries order-item lifecycle detail model."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.sql import func

from kunpeng.core.database import Base


class DWMWBOrderLifecycleDetail(Base):
    """One canonical WB order item per shop and SRID."""

    __tablename__ = "dwm_wb_order_lifecycle_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    srid = Column(String(255), primary_key=True, nullable=False, comment="订单唯一ID")

    order_id = Column(BigInteger, nullable=True, comment="Marketplace组装订单ID")
    order_uid = Column(String(255), nullable=True, comment="Marketplace订单购物车ID")
    supply_id = Column(String(255), nullable=True, comment="FBS供货单ID")
    sticker_id = Column(String(255), nullable=True, comment="订单贴纸ID")
    g_number = Column(String(255), nullable=True, comment="订单组号")

    nm_id = Column(BigInteger, nullable=True, comment="WB商品ID")
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")
    barcode = Column(String(255), nullable=True, comment="条码")
    product_title = Column(Text, nullable=True, comment="商品名称")
    product_title_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    subject_name = Column(String(255), nullable=True, comment="商品品类")
    subject_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")
    tech_size = Column(String(100), nullable=True, comment="尺码")
    tech_size_cn = Column(String(100), nullable=True, comment="尺码（中文）")

    delivery_type = Column(String(50), nullable=True, comment="Marketplace配送类型")
    warehouse_name = Column(String(255), nullable=True, comment="仓库名称")
    warehouse_name_cn = Column(String(255), nullable=True, comment="仓库名称（中文）")
    country_name = Column(String(255), nullable=True, comment="国家")
    country_name_cn = Column(String(255), nullable=True, comment="国家（中文）")
    region_name = Column(String(255), nullable=True, comment="地区")
    region_name_cn = Column(String(255), nullable=True, comment="地区（中文）")

    total_price = Column(Numeric(18, 2), nullable=True, comment="订单原价")
    price_with_disc = Column(Numeric(18, 2), nullable=True, comment="折后价格")
    finished_price = Column(Numeric(18, 2), nullable=True, comment="最终价格")
    converted_price = Column(
        Numeric(18, 2), nullable=True, comment="Marketplace折算价格"
    )
    currency_code = Column(Integer, nullable=True, comment="Marketplace货币代码")

    order_at = Column(DateTime(timezone=True), nullable=False, comment="下单时间")
    last_change_at = Column(
        DateTime(timezone=True), nullable=True, comment="订单最后修改时间"
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True, comment="取消时间")

    supplier_status = Column(String(100), nullable=True, comment="卖家处理状态")
    supplier_status_cn = Column(
        String(100), nullable=True, comment="卖家处理状态（中文）"
    )
    wb_status = Column(String(100), nullable=True, comment="WB当前状态")
    wb_status_cn = Column(String(100), nullable=True, comment="WB当前状态（中文）")
    lifecycle_stage = Column(String(50), nullable=False, comment="归一化生命周期阶段")
    lifecycle_stage_cn = Column(
        String(100), nullable=False, comment="归一化生命周期阶段中文"
    )
    is_cancelled = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否取消"
    )
    is_sold = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否有可靠售出证据"
    )
    is_terminal = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否终态"
    )

    supply_name = Column(String(500), nullable=True, comment="供货单名称")
    supply_is_done = Column(Boolean, nullable=True, comment="供货单是否完成")
    supply_created_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单创建时间"
    )
    supply_scan_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单扫描时间"
    )
    supply_closed_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单关闭时间"
    )
    supply_rejected_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单拒绝时间"
    )

    sale_at = Column(
        DateTime(timezone=True), nullable=True, comment="销售接口确认的成交时间"
    )
    sale_last_change_at = Column(
        DateTime(timezone=True), nullable=True, comment="销售记录最后修改时间"
    )
    sale_id = Column(String(255), nullable=True, comment="销售事件ID")
    sale_event_type = Column(String(20), nullable=True, comment="销售事件类型")
    finance_row_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="关联财务明细数"
    )
    finance_sale_row_cnt = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="正向销售财务明细数",
    )
    finance_first_sale_at = Column(
        DateTime(timezone=True), nullable=True, comment="首次正向财务销售时间"
    )

    return_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已关联退货记录数"
    )
    latest_return_srid = Column(String(255), nullable=True, comment="最新退货记录SRID")
    latest_return_order_id = Column(
        BigInteger, nullable=True, comment="最新退货组装订单ID"
    )
    latest_return_status = Column(String(255), nullable=True, comment="最新退货状态")
    latest_return_status_cn = Column(
        String(255), nullable=True, comment="最新退货状态（中文）"
    )
    latest_return_type = Column(String(255), nullable=True, comment="最新退货类型")
    latest_return_type_cn = Column(
        String(255), nullable=True, comment="最新退货类型（中文）"
    )
    latest_return_reason = Column(String(500), nullable=True, comment="最新退货原因")
    latest_return_reason_cn = Column(
        String(500), nullable=True, comment="最新退货原因（中文）"
    )
    return_ready_at = Column(
        DateTime(timezone=True), nullable=True, comment="最近退货待领取时间"
    )
    return_completed_at = Column(
        DateTime(timezone=True), nullable=True, comment="最近退货领取完成时间"
    )
    return_expired_at = Column(
        DateTime(timezone=True), nullable=True, comment="最近退货过期时间"
    )
    return_link_method = Column(String(50), nullable=True, comment="退货与订单关联方法")
    has_return_identity_conflict = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="退货身份关联是否冲突",
    )

    has_statistics_order_data = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否有统计订单来源"
    )
    has_marketplace_order_data = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="是否有Marketplace订单来源",
    )
    has_supply_data = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="是否有关联供货单来源",
    )
    has_sale_data = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否有销售接口来源"
    )
    has_finance_data = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否有财务明细来源"
    )
    has_return_data = Column(
        Boolean, nullable=False, server_default=text("0"), comment="是否有关联退货来源"
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
        Index("idx_dwm_wb_lifecycle_order_at", "shop_id", "order_at"),
        Index("idx_dwm_wb_lifecycle_order_id", "shop_id", "order_id"),
        Index("idx_dwm_wb_lifecycle_nm_id", "shop_id", "nm_id"),
        Index("idx_dwm_wb_lifecycle_stage", "shop_id", "lifecycle_stage"),
        Index("idx_dwm_wb_lifecycle_wb_status", "shop_id", "wb_status"),
        Index("idx_dwm_wb_lifecycle_supply", "shop_id", "supply_id"),
        {
            "comment": "DWM-WB订单商品生命周期明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
