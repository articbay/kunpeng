"""Wildberries order business detail model."""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Integer,
                        Numeric, String, Text)

from kunpeng.core.database import Base


class DWDWBOrderDetail(Base):
    """One cleaned Wildberries Marketplace order per shop."""

    __tablename__ = "dwd_wb_order_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    order_id = Column(BigInteger, primary_key=True, nullable=False, comment="工作编号")
    supply_id = Column(String(255), nullable=True, comment="供货ID")
    sticker_id = Column(String(255), nullable=True, comment="贴纸ID")
    order_dt = Column(DateTime(timezone=True), nullable=True, comment="创建日期")
    title = Column(Text, nullable=True, comment="商品名称")
    title_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    tech_size = Column(String(100), nullable=True, comment="尺寸")
    tech_size_cn = Column(String(100), nullable=True, comment="尺寸（中文）")
    color = Column(String(100), nullable=True, comment="颜色")
    color_cn = Column(String(100), nullable=True, comment="颜色（中文）")
    barcode_ori = Column(String(255), nullable=True, comment="原生条形码")
    barcode_hand = Column(String(255), nullable=True, comment="手调条形码")
    retail_price = Column(Numeric(18, 2), nullable=True, comment="零售价")
    currency = Column(String(10), nullable=True, comment="货币")
    nm_id = Column(BigInteger, nullable=True, comment="WB货号")
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")
    warehouse_id = Column(BigInteger, nullable=True, comment="卖家仓库ID")
    warehouse_name = Column(String(255), nullable=True, comment="卖家仓库")
    warehouse_name_cn = Column(String(255), nullable=True, comment="卖家仓库（中文）")
    wb_status = Column(String(100), nullable=True, comment="工作状态")
    wb_status_cn = Column(String(100), nullable=True, comment="工作状态（中文）")
    address = Column(Text, nullable=True, comment="地址")
    address_cn = Column(Text, nullable=True, comment="地址（中文）")
    is_b2b = Column(Boolean, nullable=True, comment="是否B2B")
    delivery_type = Column(String(50), nullable=True, comment="配送类型")
    supplier_status = Column(String(100), nullable=True, comment="卖家处理状态")
    supplier_status_cn = Column(
        String(100), nullable=True, comment="卖家处理状态（中文）"
    )
    is_cancellable = Column(Boolean, nullable=True, comment="是否可取消")
    price = Column(Numeric(18, 2), nullable=True, comment="订单价格")
    converted_price = Column(Numeric(18, 2), nullable=True, comment="折算价格")
    currency_code = Column(Integer, nullable=True, comment="货币代码")
    converted_currency_code = Column(Integer, nullable=True, comment="折算币种代码")
    office_id = Column(BigInteger, nullable=True, comment="配送办公点ID")
    cargo_type = Column(Integer, nullable=True, comment="货物类型")
    cross_border_type = Column(Integer, nullable=True, comment="跨境类型")
    is_zero_order = Column(Boolean, nullable=True, comment="是否零订单")

    __table_args__ = (
        Index("idx_dwd_wb_order_nm_id", "nm_id"),
        Index("idx_dwd_wb_order_order_dt", "order_dt"),
        Index("idx_dwd_wb_order_wb_status", "wb_status"),
        Index("idx_dwd_wb_order_supply_id", "supply_id"),
        Index("idx_dwd_wb_order_sticker_id", "sticker_id"),
        Index("idx_dwd_wb_order_supplier_status", "supplier_status"),
        {
            "comment": "Wildberries订单业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
