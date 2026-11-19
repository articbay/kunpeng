"""
Ozon ODS 层 - 评价相关表
"""

from sqlalchemy import (JSON, BigInteger, Boolean, Column, Date, DateTime,
                        Index, Integer, Numeric, String, UniqueConstraint)
from sqlalchemy.dialects.mysql import DECIMAL, TEXT, VARCHAR
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonReview(BaseModel):
    """
    Ozon ODS 层 - 评价表

    描述: 存储Ozon商品评价数据，包含评价内容、评分、发布时间、图片视频数量、回复信息等完整评价数据。
    """

    __tablename__ = "ods_ozon_reviews"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "review_id", name="uq_ods_ozon_reviews_shop_review_id"
        ),
        Index("idx_ods_ozon_reviews_shop_id", "shop_id"),
        Index("idx_ods_ozon_reviews_sku", "sku"),
        Index("idx_ods_ozon_reviews_published_at", "published_at"),
        {"comment": "Ozon评价表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    review_id = Column(
        VARCHAR(64),
        nullable=True,
        comment="评价ID (v2接口返回的 UUID 字符串)",
    )
    sku = Column(BigInteger, nullable=True, comment="商品SKU")
    text = Column(TEXT, nullable=True, comment="评价内容")
    published_at = Column(DateTime(timezone=True), nullable=True, comment="发布时间")
    created_at = Column(
        DateTime(timezone=True), nullable=True, comment="API返回的创建时间"
    )
    status = Column(VARCHAR(50), nullable=True, comment="评价状态")
    rating = Column(Integer, nullable=True, comment="评分 (1-5)")
    photos_amount = Column(Integer, nullable=True, comment="照片数量")
    videos_amount = Column(Integer, nullable=True, comment="视频数量")
    comments_amount = Column(Integer, nullable=True, comment="评论数量")
    order_status = Column(VARCHAR(50), nullable=True, comment="订单状态")
    product_name = Column(VARCHAR(255), nullable=True, comment="商品名称")
    is_editable = Column(Boolean, nullable=True, comment="是否可编辑")
    is_replyable = Column(Boolean, nullable=True, comment="是否可回复")
    reply = Column(TEXT, nullable=True, comment="回复内容")
    reply_created_at = Column(
        DateTime(timezone=True), nullable=True, comment="回复创建时间"
    )
