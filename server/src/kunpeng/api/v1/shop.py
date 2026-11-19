from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import (get_current_active_superuser, get_current_user,
                              get_db)
from kunpeng.crud import shop_crud
from kunpeng.models.user import User
from kunpeng.schemas.common import MessageResponse
from kunpeng.schemas.shop import ShopCreate, ShopResponse, ShopUpdate

router = APIRouter(tags=["店铺管理"])


@router.get("/shops", response_model=List[ShopResponse])
async def list_shops(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """获取当前用户的店铺列表"""
    shops = await shop_crud.get_accessible_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return shops


@router.post("/shops", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
async def create_shop(
    shop_in: ShopCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """创建店铺"""
    shop_data = shop_in.model_dump()
    shop_data["user_id"] = current_user.id
    shop = await shop_crud.create(db, obj_in=shop_data)
    return shop


@router.get("/shops/{shop_id}", response_model=ShopResponse)
async def get_shop(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个店铺详情"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop or not await shop_crud.user_can_access(
        db, user_id=current_user.id, shop_id=shop_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在",
        )
    return shop


@router.put("/shops/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: int,
    shop_in: ShopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """更新店铺"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop or shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在",
        )
    # 仅更新显式提交的字段；敏感字段留空表示"保持原值不变"，
    # 避免前端回显的脱敏掩码把真实密钥覆盖掉
    update_data = shop_in.model_dump(exclude_unset=True)
    for sensitive_field in ("api_key", "performance_client_secret"):
        if sensitive_field in update_data and not update_data[sensitive_field]:
            update_data.pop(sensitive_field)
    shop = await shop_crud.update(db, db_obj=shop, obj_in=update_data)
    return shop


@router.delete("/shops/{shop_id}", response_model=MessageResponse)
async def delete_shop(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """删除店铺"""
    shop = await shop_crud.get(db, id=shop_id)
    if not shop or shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在",
        )
    await shop_crud.remove(db, id=shop_id)
    return MessageResponse(message="店铺删除成功")
