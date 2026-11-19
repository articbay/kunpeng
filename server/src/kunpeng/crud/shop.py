from typing import List, Optional, Sequence

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.shop import Shop
from kunpeng.models.user_shop_access import UserShopAccess


class CRUDShop(CRUDBase[Shop, dict, dict]):
    """店铺CRUD"""

    async def get_by_user(
        self, db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Shop]:
        """获取用户的所有店铺"""
        result = await db.execute(
            select(Shop).where(Shop.user_id == user_id).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_accessible_by_user(
        self, db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Shop]:
        """Return shops owned by or explicitly granted to a user."""
        granted_shop_ids = select(UserShopAccess.shop_id).where(
            UserShopAccess.user_id == user_id
        )
        result = await db.execute(
            select(Shop)
            .where(or_(Shop.user_id == user_id, Shop.id.in_(granted_shop_ids)))
            .order_by(Shop.id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_platform_id(
        self, db: AsyncSession, *, platform: str, platform_shop_id: str
    ) -> Optional[Shop]:
        """根据平台ID获取店铺"""
        result = await db.execute(
            select(Shop).where(
                Shop.platform == platform, Shop.platform_shop_id == platform_shop_id
            )
        )
        return result.scalar_one_or_none()

    async def get_ids_by_user_platform(
        self, db: AsyncSession, *, user_id: int, platform: str
    ) -> List[int]:
        """Return every shop ID a user owns on one platform."""
        result = await db.execute(
            select(Shop.id).where(Shop.user_id == user_id, Shop.platform == platform)
        )
        return list(result.scalars().all())

    async def get_accessible_ids_by_user_platform(
        self, db: AsyncSession, *, user_id: int, platform: str
    ) -> List[int]:
        """Return owned and granted shop IDs for one platform."""
        granted_shop_ids = select(UserShopAccess.shop_id).where(
            UserShopAccess.user_id == user_id
        )
        result = await db.execute(
            select(Shop.id).where(
                Shop.platform == platform,
                or_(Shop.user_id == user_id, Shop.id.in_(granted_shop_ids)),
            )
        )
        return list(result.scalars().all())

    async def get_names_by_ids(
        self, db: AsyncSession, *, shop_ids: Sequence[int]
    ) -> dict[int, str]:
        """Return shop names keyed by internal shop ID."""
        if not shop_ids:
            return {}
        result = await db.execute(
            select(Shop.id, Shop.name).where(Shop.id.in_(shop_ids))
        )
        return {shop_id: shop_name for shop_id, shop_name in result.all()}

    async def user_can_access(
        self, db: AsyncSession, *, user_id: int, shop_id: int
    ) -> bool:
        granted_shop_ids = select(UserShopAccess.shop_id).where(
            UserShopAccess.user_id == user_id
        )
        result = await db.execute(
            select(Shop.id).where(
                Shop.id == shop_id,
                or_(Shop.user_id == user_id, Shop.id.in_(granted_shop_ids)),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_granted_shop_ids(
        self, db: AsyncSession, *, user_id: int, owner_id: int
    ) -> List[int]:
        result = await db.execute(
            select(UserShopAccess.shop_id)
            .join(Shop, Shop.id == UserShopAccess.shop_id)
            .where(
                UserShopAccess.user_id == user_id,
                Shop.user_id == owner_id,
            )
        )
        return list(result.scalars().all())

    async def replace_grants_for_owner(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        owner_shop_ids: List[int],
        granted_shop_ids: List[int],
    ) -> None:
        if owner_shop_ids:
            await db.execute(
                delete(UserShopAccess).where(
                    UserShopAccess.user_id == user_id,
                    UserShopAccess.shop_id.in_(owner_shop_ids),
                )
            )
        db.add_all(
            UserShopAccess(user_id=user_id, shop_id=shop_id)
            for shop_id in granted_shop_ids
        )
        await db.commit()


shop_crud = CRUDShop(Shop)
