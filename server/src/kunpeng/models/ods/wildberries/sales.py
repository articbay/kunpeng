"""
ODS 层 - 销售数据模型
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBSupplierSale(BaseModel):
    """
    ODS 层 - Wildberries 供应商销售数据
    存储 API 返回的原始销售数据，每行一条记录
    """

    __tablename__ = "ods_wb_supplier_sales"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    # 关联店铺
    shop_id = Column(Integer, nullable=False, comment="店铺ID")

    # 展开字段（用于快速查询）
    date = Column(DateTime(timezone=True), nullable=True, comment="销售日期")
    last_change_date = Column(
        DateTime(timezone=True), nullable=True, comment="最后修改日期"
    )
    warehouse_name = Column(String(255), nullable=True, comment="仓库名称")
    warehouse_type = Column(String(100), nullable=True, comment="仓库类型")
    country_name = Column(String(255), nullable=True, comment="国家名称")
    oblast_okrug_name = Column(String(255), nullable=True, comment="地区名称")
    region_name = Column(String(255), nullable=True, comment="区域名称")
    supplier_article = Column(String(255), nullable=True, comment="供应商货号")
    nm_id = Column(Integer, nullable=True, comment="商品ID")
    barcode = Column(String(255), nullable=True, comment="条码 (API: barcode)")
    category = Column(String(255), nullable=True, comment="品类")
    subject = Column(String(255), nullable=True, comment="主题")
    brand = Column(String(255), nullable=True, comment="品牌")
    tech_size = Column(String(100), nullable=True, comment="尺码")
    income_id = Column(Integer, nullable=True, comment="收入ID")
    is_supply = Column(Boolean, nullable=True, comment="是否供货")
    is_realization = Column(Boolean, nullable=True, comment="是否实现")
    total_price = Column(Numeric(18, 2), nullable=True, comment="总价")
    discount_percent = Column(Integer, nullable=True, comment="折扣百分比")
    spp = Column(Numeric(5, 2), nullable=True, comment="SPP")
    payment_sale_amount = Column(Numeric(18, 2), nullable=True, comment="支付销售金额")
    for_pay = Column(Numeric(18, 2), nullable=True, comment="应付金额")
    finished_price = Column(Numeric(18, 2), nullable=True, comment="最终价格")
    price_with_disc = Column(Numeric(18, 2), nullable=True, comment="折扣后价格")
    sale_id = Column(String(255), nullable=True, comment="销售ID")
    sticker = Column(String(255), nullable=True, comment="贴纸")
    g_number = Column(String(255), nullable=True, comment="G编号")
    srid = Column(String(255), nullable=False, comment="SRID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    __table_args__ = (
        UniqueConstraint("shop_id", "srid", name="uq_ods_sale_shop_srid"),
        Index("idx_ods_sale_shop_id", "shop_id"),
        Index("idx_ods_sale_date", "date"),
        Index("idx_ods_sale_nm_id", "nm_id"),
        {"comment": "Wildberries 供应商销售数据表"},
    )


class ODSWBSupplierOrder(BaseModel):
    """
    ODS 层 - Wildberries 供应商订单数据
    存储 API 返回的原始订单数据，每行一条记录
    """

    __tablename__ = "ods_wb_supplier_orders"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    # 关联店铺
    shop_id = Column(Integer, nullable=False, comment="店铺ID")

    # 展开字段（用于快速查询）
    date = Column(DateTime(timezone=True), nullable=True, comment="订单日期")
    last_change_date = Column(
        DateTime(timezone=True), nullable=True, comment="最后修改日期"
    )
    warehouse_name = Column(String(255), nullable=True, comment="仓库名称")
    country_name = Column(String(255), nullable=True, comment="国家名称")
    oblast_okrug_name = Column(String(255), nullable=True, comment="地区名称")
    region_name = Column(String(255), nullable=True, comment="区域名称")
    supplier_article = Column(String(255), nullable=True, comment="供应商货号")
    nm_id = Column(Integer, nullable=True, comment="商品ID")
    barcode = Column(String(255), nullable=True, comment="条码 (API: barcode)")
    category = Column(String(255), nullable=True, comment="品类")
    subject = Column(String(255), nullable=True, comment="主题")
    brand = Column(String(255), nullable=True, comment="品牌")
    tech_size = Column(String(100), nullable=True, comment="尺码")
    income_id = Column(Integer, nullable=True, comment="收入ID")
    is_supply = Column(Boolean, nullable=True, comment="是否供货")
    is_realization = Column(Boolean, nullable=True, comment="是否实现")
    total_price = Column(Numeric(18, 2), nullable=True, comment="总价")
    discount_percent = Column(Integer, nullable=True, comment="折扣百分比")
    spp = Column(Numeric(5, 2), nullable=True, comment="SPP")
    finished_price = Column(Numeric(18, 2), nullable=True, comment="最终价格")
    price_with_disc = Column(Numeric(18, 2), nullable=True, comment="折扣后价格")
    is_cancel = Column(Boolean, nullable=True, comment="是否取消")
    cancel_date = Column(DateTime(timezone=True), nullable=True, comment="取消日期")
    order_type = Column(String(100), nullable=True, comment="订单类型")
    sticker = Column(String(255), nullable=True, comment="贴纸")
    g_number = Column(String(255), nullable=True, comment="G编号")
    srid = Column(String(255), nullable=True, comment="SRID")
    odid = Column(String(255), nullable=True, comment="ODID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    __table_args__ = (
        UniqueConstraint("shop_id", "srid", name="uq_ods_order_shop_srid"),
        Index("idx_ods_order_shop_id", "shop_id"),
        Index("idx_ods_order_date", "date"),
        Index("idx_ods_order_nm_id", "nm_id"),
        Index("idx_ods_order_is_cancel", "is_cancel"),
        {"comment": "Wildberries 供应商订单数据表"},
    )
