"""
Ozon ODS 层 - 商品信息表
"""

from sqlalchemy import (JSON, BigInteger, Column, Index, Integer,
                        UniqueConstraint)
from sqlalchemy.dialects.mysql import DECIMAL, TEXT, VARCHAR

from kunpeng.models.base import BaseModel


class ODSOzonProduct(BaseModel):
    """
    Ozon ODS 层 - 商品信息表

    描述: 存储 Ozon 商品主数据，用于补全订单、退货、评价、财务和广告报表中的 SKU、货号、商品名称等维度信息。
    """

    __tablename__ = "ods_ozon_products"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "product_id", name="uq_ods_ozon_products_shop_product"
        ),
        Index("idx_ods_ozon_products_shop_id", "shop_id"),
        Index("idx_ods_ozon_products_sku", "sku"),
        Index("idx_ods_ozon_products_offer_id", "offer_id"),
        {"comment": "Ozon商品信息表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    product_id = Column(BigInteger, nullable=True, comment="商品ID")
    sku = Column(BigInteger, nullable=True, comment="Ozon SKU")
    offer_id = Column(VARCHAR(255), nullable=True, comment="商家货号")
    name = Column(TEXT, nullable=True, comment="商品名称")
    barcode = Column(VARCHAR(255), nullable=True, comment="条形码")
    category_id = Column(BigInteger, nullable=True, comment="类目ID")
    type_id = Column(BigInteger, nullable=True, comment="商品类型ID")
    category_name = Column(VARCHAR(255), nullable=True, comment="商品品类名称")
    visibility = Column(VARCHAR(100), nullable=True, comment="可见性/状态")
    price = Column(DECIMAL(18, 4), nullable=True, comment="当前价格")
    old_price = Column(DECIMAL(18, 4), nullable=True, comment="原价")
    premium_price = Column(DECIMAL(18, 4), nullable=True, comment="Premium价格")
    currency_code = Column(VARCHAR(10), nullable=True, comment="币种")
    stocks = Column(JSON, nullable=True, comment="库存信息")
    images = Column(JSON, nullable=True, comment="图片信息")
    commissions = Column(JSON, nullable=True, comment="佣金信息")
    marketing_price = Column(DECIMAL(18, 4), nullable=True, comment="营销价格")
    min_price = Column(DECIMAL(18, 4), nullable=True, comment="最低价格")
