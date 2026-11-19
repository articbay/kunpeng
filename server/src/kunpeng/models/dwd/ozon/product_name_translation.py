"""Persistent Ozon product-name translation cache."""

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text

from kunpeng.models.base import BaseModel


class DWDOzonProductNameTranslation(BaseModel):
    """One immutable automatic translation attempt per shop and Ozon SKU."""

    __tablename__ = "dwd_ozon_product_name_translation_cache"
    __table_args__ = (
        Index("idx_dwd_ozon_product_translation_status", "translation_status"),
        {"comment": "Ozon商品名称中文翻译缓存"},
    )

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    sku = Column(BigInteger, primary_key=True, nullable=False, comment="Ozon SKU")
    source_product_name = Column(Text, nullable=False, comment="首次翻译时商品名称")
    product_name_cn = Column(Text, nullable=True, comment="缓存的中文商品名称")
    translation_status = Column(
        String(20), nullable=False, comment="pending/success/passthrough/failed"
    )
    translation_source = Column(String(30), nullable=True, comment="baidu/original")
    attempt_count = Column(Integer, nullable=False, default=0, comment="翻译尝试次数")
    translated_at = Column(
        DateTime(timezone=True), nullable=True, comment="翻译完成时间"
    )
