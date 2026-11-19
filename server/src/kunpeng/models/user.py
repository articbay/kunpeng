from sqlalchemy import Boolean, Column, String, Integer, Index, UniqueConstraint

from kunpeng.models.base import BaseModel


class User(BaseModel):
    """用户模型"""

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="哈希密码")
    full_name = Column(String(255), nullable=True, comment="全名")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否超级用户")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        {"comment": "用户表"},
    )
