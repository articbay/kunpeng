"""
Shop Pydantic Schemas
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from kunpeng.core.crypto import mask_secret


class ShopBase(BaseModel):
    """店铺基础模型"""
    model_config = ConfigDict(from_attributes=True)

    name: str
    platform: str
    platform_shop_id: Optional[str] = None
    api_key: Optional[str] = None
    performance_client_id: Optional[str] = None
    performance_client_secret: Optional[str] = None


class ShopCreate(ShopBase):
    """创建店铺"""
    pass


class ShopUpdate(BaseModel):
    """更新店铺

    敏感字段（api_key / performance_client_secret）不传或留空时保持原值不变，
    配合前端"留空表示不修改"的编辑体验，避免用掩码覆盖真实密钥。
    """
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    platform: Optional[str] = None
    platform_shop_id: Optional[str] = None
    api_key: Optional[str] = None
    performance_client_id: Optional[str] = None
    performance_client_secret: Optional[str] = None


class ShopResponse(ShopBase):
    """店铺响应

    对外返回时对敏感字段脱敏，避免明文密钥经接口泄露。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int

    @field_serializer("api_key", "performance_client_secret")
    def _mask_sensitive(self, value: Optional[str]) -> Optional[str]:
        return mask_secret(value)
