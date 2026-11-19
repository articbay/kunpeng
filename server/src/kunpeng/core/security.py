from datetime import datetime, timedelta
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from kunpeng.config import settings


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # bcrypt有72字节限制，截断密码以保持一致性
    password_bytes = plain_password.encode('utf-8')[:72]
    # 确保hashed_password是bytes
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    # bcrypt有72字节限制，截断密码以避免错误
    password_bytes = password.encode('utf-8')[:72]
    # 生成salt并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """解码JWT访问令牌"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return TokenData(user_id=user_id)
    except JWTError:
        return None
