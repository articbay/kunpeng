from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.api.deps import (get_current_active_superuser, get_current_user,
                              get_db)
from kunpeng.config import settings
from kunpeng.core.security import create_access_token
from kunpeng.crud import user_crud
from kunpeng.models.user import User
from kunpeng.schemas.auth import (ChangePassword, Token, UserCreate, UserLogin,
                                  UserResponse, UserUpdate)
from kunpeng.schemas.common import MessageResponse

router = APIRouter(tags=["认证"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """返回当前登录用户。"""
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user = await user_crud.authenticate(
        db, email=user_in.email, password=user_in.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    if not bool(user.is_active):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


# ==================== 用户管理接口 ====================


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    """创建用户（管理员）"""
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
    skip: int = 0,
    limit: int = 100,
):
    """获取用户列表"""
    users = await user_crud.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    """获取单个用户详情"""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    """更新用户信息"""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    user = await user_crud.update(
        db, db_obj=user, obj_in=user_in.model_dump(exclude_unset=True)
    )
    return user


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """删除用户"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录用户",
        )
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    await user_crud.remove(db, id=user_id)
    return MessageResponse(message="用户删除成功")


@router.put("/users/{user_id}/password", response_model=MessageResponse)
async def change_user_password(
    user_id: int,
    data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    """修改用户密码"""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    await user_crud.change_password(db, db_obj=user, new_password=data.new_password)
    return MessageResponse(message="密码修改成功")


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def toggle_user_status(
    user_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """启用/停用用户"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能停用自己",
        )
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    user.is_active = is_active  # type: ignore[assignment]
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
