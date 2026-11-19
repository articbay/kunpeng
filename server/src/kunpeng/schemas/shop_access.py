from typing import List

from pydantic import BaseModel, Field


class ShopAccessUpdate(BaseModel):
    shop_ids: List[int] = Field(default_factory=list)


class ShopAccessOption(BaseModel):
    shop_id: int
    shop_name: str
    platform: str
    granted: bool


class ShopAccessResponse(BaseModel):
    user_id: int
    shops: List[ShopAccessOption]
