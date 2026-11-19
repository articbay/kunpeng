from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import get_current_active_superuser, get_db
from kunpeng.models.user import User
from kunpeng.schemas.shop_access import ShopAccessResponse, ShopAccessUpdate
from kunpeng.services.shop_access_service import shop_access_service

router = APIRouter(tags=["店铺授权"])


@router.get("/users/{user_id}", response_model=ShopAccessResponse)
async def get_user_shop_access(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser),
) -> ShopAccessResponse:
    return await shop_access_service.get_options(
        db, owner_id=current_admin.id, user_id=user_id
    )


@router.put("/users/{user_id}", response_model=ShopAccessResponse)
async def update_user_shop_access(
    user_id: int,
    update: ShopAccessUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser),
) -> ShopAccessResponse:
    return await shop_access_service.replace_grants(
        db,
        owner_id=current_admin.id,
        user_id=user_id,
        shop_ids=update.shop_ids,
    )
