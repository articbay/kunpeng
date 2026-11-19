"""Ozon customer voice business detail model."""

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text

from kunpeng.core.database import Base


class DWDOzonCustomerVoiceDetail(Base):
    """One cleaned Ozon review per shop and review ID."""

    __tablename__ = "dwd_ozon_customer_voice_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    review_id = Column(String(64), primary_key=True, nullable=False, comment="评价ID")

    # 业务字段按《客户声音data》表头顺序排列；中文翻译紧跟原字段。
    month = Column(String(7), nullable=True, comment="月份（YYYY-MM）")
    offer_id = Column(String(255), nullable=True, comment="货号")
    sku = Column(BigInteger, nullable=True, comment="Ozon SKU")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    posting_number = Column(String(100), nullable=True, comment="订单号")
    order_status = Column(String(50), nullable=True, comment="收货状态")
    order_status_cn = Column(String(255), nullable=True, comment="收货状态（中文）")
    review_text = Column(Text, nullable=True, comment="评价文本")
    review_text_cn = Column(Text, nullable=True, comment="评价文本（中文）")
    published_at = Column(DateTime(timezone=True), nullable=True, comment="发布日期")
    review_status = Column(String(50), nullable=True, comment="评价状态")
    review_status_cn = Column(String(255), nullable=True, comment="评价状态（中文）")
    rating = Column(Integer, nullable=True, comment="评分（1-5）")
    photos_amount = Column(Integer, nullable=True, comment="照片数量")
    videos_amount = Column(Integer, nullable=True, comment="视频数量")
    comments_amount = Column(Integer, nullable=True, comment="评论回应数")

    __table_args__ = (
        Index("idx_dwd_ozon_customer_voice_published", "published_at"),
        Index("idx_dwd_ozon_customer_voice_sku", "sku"),
        Index("idx_dwd_ozon_customer_voice_offer", "offer_id"),
        Index("idx_dwd_ozon_customer_voice_status", "review_status"),
        {
            "comment": "Ozon客户声音评价业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
