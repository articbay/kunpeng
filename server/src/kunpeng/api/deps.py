from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.config import settings
from kunpeng.core.database import AsyncSessionLocal
from kunpeng.core.security import decode_access_token
from kunpeng.crud import user_crud
from kunpeng.models.user import User

# Bearer token安全scheme
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[int]:
    """从token中获取用户ID"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(credentials.credentials)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    return token_data.user_id


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_token_data),
) -> User:
    """获取当前用户"""
    user = await user_crud.get(db, id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用",
        )
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return current_user
