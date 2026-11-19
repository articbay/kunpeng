"""
Ozon ODS 层 - FBO 订单相关表（来自 Ozon 仓库的订单）
"""
from sqlalchemy import (
    Column, BigInteger, Integer, JSON, DateTime, Index, UniqueConstraint
)
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DECIMAL

from kunpeng.models.base import BaseModel


class ODSOzonFBOPosting(BaseModel):
    """
    Ozon ODS 层 - FBO订单主表

    描述: 存储 Ozon FBO（Ozon 仓库发货）订单主数据，
    来源接口 POST /v2/posting/fbo/list。对应客户第二批"来自 Ozon 仓库的订单"报表。
    """

    __tablename__ = "ods_ozon_fbo_postings"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number",
            name="uq_ods_ozon_fbo_postings_shop_posting"
        ),
        Index("idx_ods_ozon_fbo_postings_shop_id", "shop_id"),
        Index("idx_ods_ozon_fbo_postings_created_at", "created_at"),
        {"comment": "Ozon FBO订单主表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_number = Column(VARCHAR(100), nullable=False, comment="订单号")
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    order_number = Column(VARCHAR(100), nullable=True, comment="订单编号")
    status = Column(VARCHAR(50), nullable=True, comment="订单状态")
    substatus = Column(VARCHAR(50), nullable=True, comment="订单子状态")
    cancel_reason_id = Column(BigInteger, nullable=True, comment="取消原因ID")
    created_at = Column(DateTime(timezone=True), nullable=True, comment="订单创建时间")
    in_process_at = Column(DateTime(timezone=True), nullable=True, comment="处理开始时间")
    analytics_data = Column(JSON, nullable=True, comment="分析数据(城市/仓库/配送方式等)")
    financial_data = Column(JSON, nullable=True, comment="财务数据(佣金/结算等)")
    additional_data = Column(JSON, nullable=True, comment="附加数据")
    legal_info = Column(JSON, nullable=True, comment="法律信息")


class ODSOzonFBOPostingProduct(BaseModel):
    """
    Ozon ODS 层 - FBO订单商品表

    描述: 存储 FBO 订单的商品明细（SKU、名称、数量、价格等）。
    """

    __tablename__ = "ods_ozon_fbo_posting_products"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "posting_number", "sku",
            name="uq_ods_ozon_fbo_posting_products_shop_posting_sku"
        ),
        Index("idx_ods_ozon_fbo_posting_products_posting", "posting_number"),
        Index("idx_ods_ozon_fbo_posting_products_shop_id", "shop_id"),
        {"comment": "Ozon FBO订单商品表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    posting_number = Column(VARCHAR(100), nullable=False, comment="订单号")
    sku = Column(BigInteger, nullable=False, comment="商品SKU")
    name = Column(TEXT, nullable=True, comment="商品名称")
    offer_id = Column(VARCHAR(255), nullable=True, comment="商家货号")
    quantity = Column(Integer, nullable=True, comment="数量")
    price = Column(DECIMAL(18, 4), nullable=True, comment="价格")
    currency_code = Column(VARCHAR(10), nullable=True, comment="币种")
