from sqlalchemy import Column, Integer, String, Text, Index, UniqueConstraint

from kunpeng.core.crypto import EncryptedText
from kunpeng.models.base import BaseModel


class Shop(BaseModel):
    """店铺模型"""

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "shops"

    name = Column(String(255), nullable=False, comment="店铺名称")
    platform = Column(String(50), nullable=False, index=True, comment="平台(wildberries, ozon)")
    platform_shop_id = Column(String(255), nullable=True, index=True, comment="平台店铺ID")
    api_key = Column(EncryptedText, nullable=True, comment="API密钥(加密存储)")
    # Ozon Performance（广告）API 独立凭证，仅 Ozon 店铺使用；为空时回退全局配置
    performance_client_id = Column(String(255), nullable=True, comment="Ozon广告API Client-Id")
    performance_client_secret = Column(EncryptedText, nullable=True, comment="Ozon广告API Client-Secret(加密存储)")

    # 关联
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")

    __table_args__ = (
        Index("idx_shop_user_id", "user_id"),
        UniqueConstraint("user_id", "platform", "platform_shop_id", name="uq_shop_user_platform_platformid"),
        {"comment": "店铺表"},
    )
