from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.core.security import get_password_hash, verify_password
from kunpeng.crud.base import CRUDBase
from kunpeng.models.user import User
from kunpeng.schemas.auth import UserCreate, UserResponse


class CRUDUser(CRUDBase[User, UserCreate, UserResponse]):
    """用户CRUD"""

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """创建用户（自动哈希密码）"""
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_active=True,
            is_superuser=False,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        """验证用户"""
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: dict
    ) -> User:
        """更新用户信息"""
        update_data = obj_in.copy()
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def change_password(
        self, db: AsyncSession, *, db_obj: User, new_password: str
    ) -> User:
        """修改密码"""
        db_obj.hashed_password = get_password_hash(new_password)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


user_crud = CRUDUser(User)
