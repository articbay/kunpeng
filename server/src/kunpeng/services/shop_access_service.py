from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud, user_crud
from kunpeng.schemas.shop_access import ShopAccessOption, ShopAccessResponse


class ShopAccessService:
    async def get_options(
        self, db: AsyncSession, *, owner_id: int, user_id: int
    ) -> ShopAccessResponse:
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        owned_shops = await shop_crud.get_by_user(db, user_id=owner_id, limit=1000)
        granted_ids = set(
            await shop_crud.get_granted_shop_ids(db, user_id=user_id, owner_id=owner_id)
        )
        return ShopAccessResponse(
            user_id=user_id,
            shops=[
                ShopAccessOption(
                    shop_id=shop.id,
                    shop_name=shop.name,
                    platform=shop.platform,
                    granted=shop.id in granted_ids,
                )
                for shop in owned_shops
            ],
        )

    async def replace_grants(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        user_id: int,
        shop_ids: list[int],
    ) -> ShopAccessResponse:
        if owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="店铺所有者无需重复授权",
            )
        options = await self.get_options(db, owner_id=owner_id, user_id=user_id)
        owner_shop_ids = [item.shop_id for item in options.shops]
        requested_ids = set(shop_ids)
        invalid_ids = requested_ids - set(owner_shop_ids)
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能授权当前管理员拥有的店铺",
            )
        await shop_crud.replace_grants_for_owner(
            db,
            user_id=user_id,
            owner_shop_ids=owner_shop_ids,
            granted_shop_ids=sorted(requested_ids),
        )
        return await self.get_options(db, owner_id=owner_id, user_id=user_id)


shop_access_service = ShopAccessService()
