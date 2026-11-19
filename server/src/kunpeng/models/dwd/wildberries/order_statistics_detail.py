"""Wildberries statistics order business detail model."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
)

from kunpeng.core.database import Base


class DWDWBOrderStatisticsDetail(Base):
    """One cleaned WB Statistics API order per shop and SRID."""

    __tablename__ = "dwd_wb_order_statistics_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    srid = Column(String(255), primary_key=True, nullable=False, comment="系统订单号")
    order_date = Column(DateTime(timezone=True), nullable=True, comment="下单时间")
    last_change_date = Column(
        DateTime(timezone=True), nullable=True, comment="最后修改时间"
    )
    warehouse_name = Column(String(255), nullable=True, comment="仓库名称")
    warehouse_name_cn = Column(String(255), nullable=True, comment="仓库名称（中文）")
    country_name = Column(String(255), nullable=True, comment="国家")
    country_name_cn = Column(String(255), nullable=True, comment="国家（中文）")
    oblast_okrug_name = Column(String(255), nullable=True, comment="联邦管区")
    oblast_okrug_name_cn = Column(
        String(255), nullable=True, comment="联邦管区（中文）"
    )
    region_name = Column(String(255), nullable=True, comment="地区")
    region_name_cn = Column(String(255), nullable=True, comment="地区（中文）")
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")
    nm_id = Column(BigInteger, nullable=True, comment="WB货号")
    barcode_ori = Column(String(255), nullable=True, comment="原生条形码")
    barcode_hand = Column(String(255), nullable=True, comment="手调条形码")
    category = Column(String(255), nullable=True, comment="商品分类")
    category_cn = Column(String(255), nullable=True, comment="商品分类（中文）")
    subject_name = Column(String(255), nullable=True, comment="商品品类")
    subject_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")
    tech_size = Column(String(100), nullable=True, comment="尺码")
    tech_size_cn = Column(String(100), nullable=True, comment="尺码（中文）")
    total_price = Column(Numeric(18, 2), nullable=True, comment="原价")
    discount_percent = Column(Integer, nullable=True, comment="折扣百分比")
    price_with_disc = Column(Numeric(18, 2), nullable=True, comment="折后价格")
    finished_price = Column(Numeric(18, 2), nullable=True, comment="最终价格")
    is_cancel = Column(Boolean, nullable=True, comment="是否取消")
    cancel_date = Column(DateTime(timezone=True), nullable=True, comment="取消时间")
    sticker_id = Column(String(255), nullable=True, comment="贴纸ID")
    g_number = Column(String(255), nullable=True, comment="订单组号")

    __table_args__ = (
        Index("idx_dwd_wb_order_stats_order_date", "order_date"),
        Index("idx_dwd_wb_order_stats_nm_id", "nm_id"),
        Index("idx_dwd_wb_order_stats_is_cancel", "is_cancel"),
        Index("idx_dwd_wb_order_stats_warehouse", "warehouse_name"),
        Index("idx_dwd_wb_order_stats_region", "region_name"),
        {
            "comment": "Wildberries统计订单业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
