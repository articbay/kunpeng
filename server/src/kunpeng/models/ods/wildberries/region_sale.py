"""ODS 层 - Wildberries 区域销售报告模型。"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBRegionSale(BaseModel):
    """Wildberries 区域销售聚合报告。"""

    __tablename__ = "ods_wb_finance_region_sales"

    id = Column(
        BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    date_from = Column(Date, nullable=False, comment="报告开始日期")
    date_to = Column(Date, nullable=False, comment="报告结束日期")
    row_key = Column(String(64), nullable=False, comment="地区商品维度哈希")

    country_name = Column(String(100), nullable=True, comment="国家")
    fo_name = Column(String(255), nullable=True, comment="联邦区")
    region_name = Column(String(255), nullable=True, comment="地区")
    city_name = Column(String(255), nullable=True, comment="城市")
    nm_id = Column(BigInteger, nullable=True, comment="Wildberries商品ID")
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")

    sale_invoice_cost_price = Column(
        Numeric(18, 2),
        nullable=True,
        comment="销售金额",
    )
    sale_invoice_cost_price_percent = Column(
        Numeric(18, 6),
        nullable=True,
        comment="销售金额占比",
    )
    sale_item_invoice_qty = Column(Integer, nullable=True, comment="销售数量")

    row_data = Column(JSON, nullable=False, comment="API原始JSON数据")
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "row_key",
            name="uq_ods_wb_region_sale_shop_window_row",
        ),
        Index("idx_ods_wb_region_sale_shop_id", "shop_id"),
        Index("idx_ods_wb_region_sale_date_range", "date_from", "date_to"),
        Index("idx_ods_wb_region_sale_nm_id", "nm_id"),
        Index("idx_ods_wb_region_sale_region_name", "region_name"),
        {"comment": "Wildberries区域销售报告表"},
    )
